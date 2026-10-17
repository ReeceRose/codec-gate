Ext.ns('Deluge.ux.preferences');
Ext.ns('Deluge.plugins');

Deluge.ux.preferences.CodecGatePage = Ext.extend(Ext.Panel, {
    title: _('CodecGate'),
    header: false,
    border: false,
    layout: 'form',
    autoScroll: true,

    initComponent: function () {
        Deluge.ux.preferences.CodecGatePage.superclass.initComponent.call(this);

        var codecs = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Codecs'),
            autoHeight: true,
            labelAlign: 'top',
            defaults: { width: 320 },
        });
        codecs.add({
            xtype: 'box',
            autoEl: {
                tag: 'div',
                style: 'margin-bottom: 8px; color: #666;',
                html: _(
                    'One pattern per line, matched case-insensitively as a whole word ' +
                        'against the torrent and video file names. Patterns are regular ' +
                        'expressions, e.g. <code>x\\.?264</code> matches x264 and x.264. ' +
                        'Hold patterns win if both match.'
                ),
            },
        });
        this.holdPatterns = codecs.add({
            xtype: 'textarea',
            fieldLabel: _('Hold for approval'),
            height: 80,
        });
        this.allowPatterns = codecs.add({
            xtype: 'textarea',
            fieldLabel: _('Always allow'),
            height: 80,
        });

        var behaviour = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Behaviour'),
            autoHeight: true,
            labelWidth: 110,
        });
        this.holdUnknown = behaviour.add({
            xtype: 'checkbox',
            hideLabel: true,
            boxLabel: _('Hold videos that match neither list'),
        });
        this.holdLabel = behaviour.add({
            xtype: 'textfield',
            fieldLabel: _('Hold label'),
            width: 180,
        });
        behaviour.add({
            xtype: 'box',
            autoEl: {
                tag: 'div',
                style: 'margin-bottom: 8px; color: #666;',
                html: _('Needs the Label plugin. Leave blank to only pause.'),
            },
        });
        this.videoExtensions = behaviour.add({
            xtype: 'textfield',
            fieldLabel: _('Video extensions'),
            width: 300,
        });

        var older = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Older releases'),
            autoHeight: true,
            labelWidth: 110,
        });
        this.allowOlder = older.add({
            xtype: 'checkbox',
            hideLabel: true,
            boxLabel: _('Auto-allow releases from before the year below, whatever the codec'),
        });
        this.olderThanYear = older.add({
            xtype: 'numberfield',
            fieldLabel: _('Before year'),
            width: 80,
            allowDecimals: false,
            allowNegative: false,
            minValue: 1900,
            maxValue: 2100,
        });
        older.add({
            xtype: 'box',
            autoEl: {
                tag: 'div',
                style: 'margin-bottom: 8px; color: #666;',
                html: _(
                    'The year is read from the name, e.g. Movie.1998.1080p.x264. ' +
                        'Names without a year are not affected.'
                ),
            },
        });

        var notifications = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Notifications'),
            autoHeight: true,
            labelWidth: 110,
        });
        this.webhookUrl = notifications.add({
            xtype: 'textfield',
            fieldLabel: _('Webhook URL'),
            width: 300,
            emptyText: 'https://discord.com/api/webhooks/...',
        });
        this.webhookFormat = notifications.add({
            xtype: 'combo',
            fieldLabel: _('Format'),
            width: 140,
            mode: 'local',
            store: [
                ['json', _('Generic JSON')],
                ['discord', _('Discord')],
            ],
            triggerAction: 'all',
            editable: false,
            forceSelection: true,
        });
        this.notifyHeld = notifications.add({
            xtype: 'checkbox',
            hideLabel: true,
            boxLabel: _('Notify when a torrent is held'),
        });
        this.notifyAllowed = notifications.add({
            xtype: 'checkbox',
            hideLabel: true,
            boxLabel: _('Notify when a torrent is allowed'),
        });
        notifications.add({
            xtype: 'button',
            text: _('Send test'),
            handler: this.onTestWebhook,
            scope: this,
        });
        this.webhookResult = notifications.add({
            xtype: 'box',
            autoEl: { tag: 'div', style: 'margin-top: 8px;', html: '&nbsp;' },
        });

        var test = this.add({
            xtype: 'fieldset',
            border: false,
            title: _('Test a name'),
            autoHeight: true,
            labelAlign: 'top',
        });
        this.testName = test.add({
            xtype: 'textfield',
            fieldLabel: _('Release name (uses the settings above, saved or not)'),
            width: 320,
            enableKeyEvents: true,
            listeners: {
                specialkey: function (field, e) {
                    if (e.getKey() == e.ENTER) this.onTest();
                },
                scope: this,
            },
        });
        test.add({
            xtype: 'button',
            text: _('Test'),
            handler: this.onTest,
            scope: this,
        });
        this.testResult = test.add({
            xtype: 'box',
            autoEl: { tag: 'div', style: 'margin-top: 8px; font-weight: bold;', html: '&nbsp;' },
        });

        this.on('show', this.loadConfig, this);
    },

    splitLines: function (text) {
        return Ext.isEmpty(text) ? [] : text.split(/\r?\n/);
    },

    getFormConfig: function () {
        return {
            hold_patterns: this.splitLines(this.holdPatterns.getValue()),
            allow_patterns: this.splitLines(this.allowPatterns.getValue()),
            hold_unknown: this.holdUnknown.getValue(),
            hold_label: this.holdLabel.getValue(),
            video_extensions: this.videoExtensions.getValue().split(/[\s,]+/),
            allow_older: this.allowOlder.getValue(),
            older_than_year: this.olderThanYear.getValue(),
            webhook_url: this.webhookUrl.getValue(),
            webhook_format: this.webhookFormat.getValue(),
            notify_held: this.notifyHeld.getValue(),
            notify_allowed: this.notifyAllowed.getValue(),
        };
    },

    loadConfig: function () {
        deluge.client.codecgate.get_config({
            success: function (config) {
                this.holdPatterns.setValue(config.hold_patterns.join('\n'));
                this.allowPatterns.setValue(config.allow_patterns.join('\n'));
                this.holdUnknown.setValue(config.hold_unknown);
                this.holdLabel.setValue(config.hold_label);
                this.videoExtensions.setValue(config.video_extensions.join(' '));
                this.allowOlder.setValue(config.allow_older);
                this.olderThanYear.setValue(config.older_than_year);
                this.webhookUrl.setValue(config.webhook_url);
                this.webhookFormat.setValue(config.webhook_format);
                this.notifyHeld.setValue(config.notify_held);
                this.notifyAllowed.setValue(config.notify_allowed);
            },
            scope: this,
        });
    },

    errorMessage: function (response) {
        var error = response && response.error;
        return error && error.message ? error.message : _('Unknown error');
    },

    onTest: function () {
        var name = this.testName.getValue();
        if (Ext.isEmpty(name)) return;
        deluge.client.codecgate.test_name(name, this.getFormConfig(), {
            success: function (decision) {
                var text = {
                    hold: _('Held for approval'),
                    allow: _('Allowed'),
                    ignore: _('Ignored'),
                }[decision.action];
                this.testResult.update(
                    Ext.util.Format.htmlEncode(text + ' (' + decision.reason + ')')
                );
            },
            failure: function (error) {
                this.testResult.update(Ext.util.Format.htmlEncode(this.errorMessage(error)));
            },
            scope: this,
        });
    },

    onTestWebhook: function () {
        this.webhookResult.update(_('Sending...'));
        deluge.client.codecgate.test_webhook(this.getFormConfig(), {
            success: function (status) {
                this.webhookResult.update(_('Sent') + ' (HTTP ' + status + ')');
            },
            failure: function (response) {
                this.webhookResult.update(Ext.util.Format.htmlEncode(this.errorMessage(response)));
            },
            scope: this,
        });
    },

    onApply: function () {
        deluge.client.codecgate.set_config(this.getFormConfig(), {
            success: this.loadConfig,
            failure: function (error) {
                Ext.MessageBox.alert(_('CodecGate'), Ext.util.Format.htmlEncode(this.errorMessage(error)));
            },
            scope: this,
        });
    },

    onOk: function () {
        this.onApply();
    },
});

Deluge.plugins.CodecGatePlugin = Ext.extend(Deluge.Plugin, {
    name: 'CodecGate',

    onDisable: function () {
        deluge.preferences.removePage(this.prefsPage);
    },

    onEnable: function () {
        this.prefsPage = deluge.preferences.addPage(new Deluge.ux.preferences.CodecGatePage());
    },
});

Deluge.registerPlugin('CodecGate', Deluge.plugins.CodecGatePlugin);
