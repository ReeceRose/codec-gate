import logging

from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread

import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
from deluge.plugins.pluginbase import CorePluginBase

from . import notify, rules
from .rules import DEFAULT_PREFS

log = logging.getLogger(__name__)

POLL_SECONDS = 1


class Core(CorePluginBase):
    def enable(self):
        self.config = deluge.configmanager.ConfigManager('codecgate.conf', DEFAULT_PREFS)
        self.torrent_manager = component.get('TorrentManager')
        # Magnets have no file list until metadata arrives, so poll for them.
        self.pending = set()

        event_manager = component.get('EventManager')
        event_manager.register_event_handler('TorrentAddedEvent', self.on_torrent_added)
        event_manager.register_event_handler('TorrentRemovedEvent', self.on_torrent_removed)
        event_manager.register_event_handler('TorrentResumedEvent', self.on_torrent_resumed)

        self.poller = LoopingCall(self.check_pending)
        self.poller.start(POLL_SECONDS, now=False)

    def disable(self):
        if self.poller.running:
            self.poller.stop()
        event_manager = component.get('EventManager')
        event_manager.deregister_event_handler('TorrentAddedEvent', self.on_torrent_added)
        event_manager.deregister_event_handler('TorrentRemovedEvent', self.on_torrent_removed)
        event_manager.deregister_event_handler('TorrentResumedEvent', self.on_torrent_resumed)
        self.config.save()

    def update(self):
        pass

    # Events

    def on_torrent_added(self, torrent_id, from_state):
        # from_state means it was loaded at startup; it's already been judged.
        if from_state:
            return
        if not self.evaluate(torrent_id):
            self.pending.add(torrent_id)

    def on_torrent_removed(self, torrent_id):
        self.pending.discard(torrent_id)

    def on_torrent_resumed(self, torrent_id):
        # Resuming a held torrent approves it, so drop the hold label.
        label = self.config['hold_label']
        label_core = self._label_core()
        if not label or not label_core:
            return
        # Deluge's own resume-on-add alert can arrive after we've paused it;
        # only a real resume (running, or queued by auto-management) is approval.
        try:
            status = self.torrent_manager[torrent_id].handle.status()
            if status.paused and not status.auto_managed:
                return
        except KeyError:
            return
        if label_core.torrent_labels.get(torrent_id) == label:
            label_core.set_torrent(torrent_id, '')
            log.info('CodecGate: %s approved, cleared label', torrent_id)

    def check_pending(self):
        for torrent_id in list(self.pending):
            if self.evaluate(torrent_id):
                self.pending.discard(torrent_id)

    # Logic

    def evaluate(self, torrent_id):
        """Judge a torrent. Returns False if it needs to be retried later."""
        try:
            torrent = self.torrent_manager[torrent_id]
        except KeyError:
            return True
        if not torrent.handle.status().has_metadata:
            return False

        status = torrent.get_status(['name', 'files'])
        name = status['name']
        decision = rules.decide(name, [f['path'] for f in status['files']], self.config.config)
        log.info('CodecGate: %s -> %s (%s)', name, decision['action'], decision['reason'])

        if decision['action'] == rules.HOLD:
            torrent.pause()
            # Right after adding, Torrent.pause() sees a stale "paused" status
            # and skips the real pause, so pause libtorrent directly too.
            torrent.handle.pause()
            self._apply_label(torrent_id)
            if self.config['notify_held']:
                self._notify('held', name, decision, torrent_id)
        elif decision['action'] == rules.ALLOW and self.config['notify_allowed']:
            self._notify('allowed', name, decision, torrent_id)
        return True

    def _notify(self, event, name, decision, torrent_id):
        url = self.config['webhook_url']
        if not url:
            return
        payload = notify.build_payload(
            self.config['webhook_format'], event, name, decision['reason'],
            decision['year'], torrent_id,
        )
        deferToThread(notify.send, url, payload).addErrback(
            lambda failure: log.warning('CodecGate: webhook failed: %s', failure.getErrorMessage())
        )

    def _label_core(self):
        try:
            return component.get('CorePlugin.Label')
        except KeyError:
            return None

    def _apply_label(self, torrent_id):
        label = self.config['hold_label'].lower()
        if not label:
            return
        label_core = self._label_core()
        if not label_core:
            log.warning('CodecGate: Label plugin not enabled, paused without label')
            return
        # Don't clobber a label set by Sonarr/Radarr etc., they rely on it.
        if label_core.torrent_labels.get(torrent_id):
            return
        if label not in label_core.get_labels():
            label_core.add(label)
        label_core.set_torrent(torrent_id, label)

    # RPC

    @export
    def set_config(self, config):
        for key, value in rules.validate_config(config, DEFAULT_PREFS).items():
            self.config[key] = value
        self.config.save()

    @export
    def get_config(self):
        return self.config.config

    def _settings(self, config):
        settings = dict(self.config.config)
        if config:
            settings.update(rules.validate_config(config, DEFAULT_PREFS))
        return settings

    @export
    def test_name(self, name, config=None):
        """Judge a release name, optionally against unsaved settings."""
        return rules.decide(name, [], self._settings(config))

    @export
    def test_webhook(self, config=None):
        """Send a sample notification, optionally using unsaved settings."""
        settings = self._settings(config)
        if not settings['webhook_url']:
            raise ValueError('Enter a webhook URL first')
        payload = notify.build_payload(
            settings['webhook_format'], 'test',
            'Example.Movie.2009.1080p.BluRay.x264-GROUP', 'Test from the CodecGate preferences page',
        )
        return deferToThread(notify.send, settings['webhook_url'], payload)
