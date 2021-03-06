from kivy.app import App
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.lang import Builder

from electrum.util import base_units
from electrum.i18n import languages
from electrum_gui.kivy.i18n import _
from electrum.plugins import run_hook
from electrum import coinchooser
from electrum.util import fee_levels

from choice_dialog import ChoiceDialog

Builder.load_string('''
#:import partial functools.partial
#:import _ electrum_gui.kivy.i18n._

<SettingsItem@ButtonBehavior+BoxLayout>
    orientation: 'vertical'
    title: ''
    description: ''
    size_hint: 1, None
    height: '60dp'

    canvas.before:
        Color:
            rgba: (0.192, .498, 0.745, 1) if self.state == 'down' else (0.3, 0.3, 0.3, 0)
        Rectangle:
            size: self.size
            pos: self.pos
    on_release:
        Clock.schedule_once(self.action)

    Widget
    TopLabel:
        id: title
        text: self.parent.title
        bold: True
        halign: 'left'
    TopLabel:
        text: self.parent.description
        color: 0.8, 0.8, 0.8, 1
        halign: 'left'
    Widget


<SettingsDialog@Popup>
    id: settings
    title: _('Electrum Settings')
    disable_pin: False
    use_encryption: False
    BoxLayout:
        orientation: 'vertical'
        ScrollView:
            GridLayout:
                id: scrollviewlayout
                cols:1
                size_hint: 1, None
                height: self.minimum_height
                padding: '10dp'
                SettingsItem:
                    lang: settings.get_language_name()
                    title: 'Language' + ': ' + str(self.lang)
                    description: _('Language')
                    action: partial(root.language_dialog, self)
                CardSeparator
                SettingsItem:
                    status: '' if root.disable_pin else ('ON' if root.use_encryption else 'OFF')
                    disabled: root.disable_pin
                    title: _('PIN code') + ': ' + self.status
                    description: _("Change your PIN code.")
                    action: partial(root.change_password, self)
                CardSeparator
                SettingsItem:
                    bu: app.base_unit
                    title: _('Denomination') + ': ' + self.bu
                    description: _("Base unit for Bitcoin amounts.")
                    action: partial(root.unit_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.fee_status()
                    title: _('Fees') + ': ' + self.status
                    description: _("Fees paid to the Bitcoin miners.")
                    action: partial(root.fee_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.fx_status()
                    title: _('Fiat Currency') + ': ' + self.status
                    description: _("Display amounts in fiat currency.")
                    action: partial(root.fx_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.network_status()
                    title: _('Server') + ': ' + self.status
                    description: _("Select your history server.")
                    action: partial(root.network_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.proxy_status()
                    title: _('Proxy') + ': ' + self.status
                    description: _("Proxy configuration.")
                    action: partial(root.proxy_dialog, self)
                CardSeparator
                SettingsItem:
                    status: 'ON' if bool(app.plugins.get('labels')) else 'OFF'
                    title: _('Labels Sync') + ': ' + self.status
                    description: _("Save and synchronize your labels.")
                    action: partial(root.plugin_dialog, 'labels', self)
                CardSeparator
                SettingsItem:
                    status: root.rbf_status()
                    title: _('Replace-by-fee') + ': ' + self.status
                    description: _("Create replaceable transactions.")
                    action: partial(root.rbf_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.coinselect_status()
                    title: _('Coin selection') + ': ' + self.status
                    description: "Coin selection method"
                    action: partial(root.coinselect_dialog, self)
                CardSeparator
                SettingsItem:
                    status: root.blockchain_status()
                    title: _('Blockchain') + ': ' + self.status
                    description: _("Configure checkpoints")
                    action: partial(root.blockchain_dialog, self)
''')



class SettingsDialog(Factory.Popup):

    def __init__(self, app):
        self.app = app
        self.plugins = self.app.plugins
        self.config = self.app.electrum_config
        Factory.Popup.__init__(self)
        layout = self.ids.scrollviewlayout
        layout.bind(minimum_height=layout.setter('height'))
        # cached dialogs
        self._fx_dialog = None
        self._fee_dialog = None
        self._rbf_dialog = None
        self._network_dialog = None
        self._proxy_dialog = None
        self._language_dialog = None
        self._unit_dialog = None
        self._coinselect_dialog = None
        self._blockchain_dialog = None

    def update(self):
        self.wallet = self.app.wallet
        self.disable_pin = self.wallet.is_watching_only() if self.wallet else True
        self.use_encryption = self.wallet.has_password() if self.wallet else False

    def get_language_name(self):
        return languages.get(self.config.get('language', 'en_UK'), '')

    def change_password(self, item, dt):
        self.app.change_password(self.update)

    def language_dialog(self, item, dt):
        if self._language_dialog is None:
            l = self.config.get('language', 'en_UK')
            def cb(key):
                self.config.set_key("language", key, True)
                item.lang = self.get_language_name()
                self.app.language = key
            self._language_dialog = ChoiceDialog(_('Language'), languages, l, cb)
        self._language_dialog.open()

    def unit_dialog(self, item, dt):
        if self._unit_dialog is None:
            def cb(text):
                self.app._set_bu(text)
                item.bu = self.app.base_unit
            self._unit_dialog = ChoiceDialog(_('Denomination'), base_units.keys(), self.app.base_unit, cb)
        self._unit_dialog.open()

    def coinselect_status(self):
        return coinchooser.get_name(self.app.electrum_config)

    def coinselect_dialog(self, item, dt):
        if self._coinselect_dialog is None:
            choosers = sorted(coinchooser.COIN_CHOOSERS.keys())
            chooser_name = coinchooser.get_name(self.config)
            def cb(text):
                self.config.set_key('coin_chooser', text)
                item.status = text
            self._coinselect_dialog = ChoiceDialog(_('Coin selection'), choosers, chooser_name, cb)
        self._coinselect_dialog.open()

    def blockchain_status(self):
        height = self.app.network.get_local_height()
        return "%d blocks"% height

    def blockchain_dialog(self, item, dt):
        from checkpoint_dialog import CheckpointDialog
        if self._blockchain_dialog is None:
            def callback(height, value):
                if value:
                    self.app.network.blockchain.set_checkpoint(height, value)
                    item.status = self.blockchain_status()
            self._blockchain_dialog = CheckpointDialog(self.app.network, callback)
        self._blockchain_dialog.open()

    def proxy_status(self):
        server, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
        return proxy.get('host') +':' + proxy.get('port') if proxy else _('None')

    def proxy_dialog(self, item, dt):
        if self._proxy_dialog is None:
            server, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
            def callback(popup):
                if popup.ids.mode.text != 'None':
                    proxy = {
                        'mode':popup.ids.mode.text,
                        'host':popup.ids.host.text,
                        'port':popup.ids.port.text,
                        'user':popup.ids.user.text,
                        'password':popup.ids.password.text
                    }
                else:
                    proxy = None
                self.app.network.set_parameters(server, port, protocol, proxy, auto_connect)
                item.status = self.proxy_status()
            popup = Builder.load_file('gui/kivy/uix/ui_screens/proxy.kv')
            popup.ids.mode.text = proxy.get('mode') if proxy else 'None'
            popup.ids.host.text = proxy.get('host') if proxy else ''
            popup.ids.port.text = proxy.get('port') if proxy else ''
            popup.ids.user.text = proxy.get('user') if proxy else ''
            popup.ids.password.text = proxy.get('password') if proxy else ''
            popup.on_dismiss = lambda: callback(popup)
            self._proxy_dialog = popup
        self._proxy_dialog.open()

    def network_dialog(self, item, dt):
        host, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
        servers = self.app.network.get_servers()
        if self._network_dialog is None:
            def cb1(popup):
                host = str(popup.ids.host.text)
                port = str(popup.ids.port.text)
                auto_connect = popup.ids.auto_connect.active
                self.app.network.set_parameters(host, port, protocol, proxy, auto_connect)
                item.status = self.network_status()
            def cb2(host):
                from electrum.network import DEFAULT_PORTS
                pp = servers.get(host, DEFAULT_PORTS)
                port = pp.get(protocol, '')
                popup.ids.host.text = host
                popup.ids.port.text = port
            def cb3():
                ChoiceDialog(_('Choose a server'), sorted(servers), popup.ids.host.text, cb2).open()
            popup = Builder.load_file('gui/kivy/uix/ui_screens/network.kv')
            popup.ids.chooser.on_release = cb3
            popup.on_dismiss = lambda: cb1(popup)
            self._network_dialog = popup

        self._network_dialog.ids.auto_connect.active = auto_connect
        self._network_dialog.ids.host.text = host
        self._network_dialog.ids.port.text = port
        self._network_dialog.open()

    def network_status(self):
        server, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
        return 'auto-connect' if auto_connect else server

    def plugin_dialog(self, name, label, dt):
        from checkbox_dialog import CheckBoxDialog
        def callback(status):
            self.plugins.enable(name) if status else self.plugins.disable(name)
            label.status = 'ON' if status else 'OFF'

        status = bool(self.plugins.get(name))
        dd = self.plugins.descriptions.get(name)
        descr = dd.get('description')
        fullname = dd.get('fullname')
        d = CheckBoxDialog(fullname, descr, status, callback)
        d.open()

    def fee_status(self):
        if self.config.get('dynamic_fees', True):
            return fee_levels[self.config.get('fee_level', 2)]
        else:
            return self.app.format_amount_and_units(self.config.fee_per_kb()) + '/kB'

    def fee_dialog(self, label, dt):
        if self._fee_dialog is None:
            from fee_dialog import FeeDialog
            def cb():
                label.status = self.fee_status()
            self._fee_dialog = FeeDialog(self.app, self.config, cb)
        self._fee_dialog.open()

    def rbf_status(self):
        return 'ON' if self.config.get('use_rbf') else 'OFF'

    def rbf_dialog(self, label, dt):
        if self._rbf_dialog is None:
            from checkbox_dialog import CheckBoxDialog
            def cb(x):
                self.config.set_key('use_rbf', x, True)
                label.status = self.rbf_status()
            msg = [_('If you check this box, your transactions will be marked as non-final,'),
                   _('and you will have the possiblity, while they are unconfirmed, to replace them with transactions that pays higher fees.'),
                   _('Note that some merchants do not accept non-final transactions until they are confirmed.')]
            fullname = _('Replace by fee')
            self._rbf_dialog = CheckBoxDialog(fullname, ' '.join(msg), self.config.get('use_rbf', False), cb)
        self._rbf_dialog.open()

    def fx_status(self):
        fx = self.app.fx
        if fx.is_enabled():
            source = fx.exchange.name()
            ccy = fx.get_currency()
            return '%s [%s]' %(ccy, source)
        else:
            return _('None')

    def fx_dialog(self, label, dt):
        if self._fx_dialog is None:
            from fx_dialog import FxDialog
            def cb():
                label.status = self.fx_status()
            self._fx_dialog = FxDialog(self.app, self.plugins, self.config, cb)
        self._fx_dialog.open()
