from aqt import mw

from aqt.qt import QMessageBox
from ..util import getPluginName
from ..Options import BooleanOption


class SettingsView:
    def __init__(self, options, deckSelected, refresh_func):
        self.options = options
        self.deckSelected = deckSelected
        self.refresh_func = refresh_func

    def main(self):
        html = "<h1>%s Settings</h1>" % getPluginName()
        html += "<h2>Global options</h2>"
        html += "<table>"
        for key, option in self.options.getGlobalOptions().items():
            if isinstance(option, BooleanOption):
                html += (
                    '<tr><td width="140">%s [<a href="SettingsView||showDescription||%s||%s">?</a>]:</td><td><a href="SettingsView||changeGlobalOption||%s">%s</a></td></tr>'
                    % (
                        option.desc,
                        option.desc,
                        option.longDesc,
                        key,
                        option.getValue(),
                    )
                )
            else:
                html += (
                    '<tr><td width="140">%s [<a href="SettingsView||showDescription||%s||%s">?</a>]:</td><td>%s</td></tr>'
                    % (option.desc, option.desc, option.longDesc, option.getValue())
                )
        html += "</table>"

        if self.deckSelected:
            html += "<h2>Current deck options</h2>"
            html += "<table>"
            for key, option in self.options.getDeckOptions().items():
                html += (
                    '<tr><td width="140">%s [<a href="SettingsView||showDescription||%s||%s"">?</a>]:</td><td><a href="SettingsView||changeDeckOption||%s">%s</a></td></tr>'
                    % (
                        option.desc,
                        option.desc,
                        option.longDesc,
                        key,
                        option.getValue(),
                    )
                )
            html += "</table><br>"

        html += '<br /><a href="MainView||main">&lt;&lt; Back to main view</a>'

        return html

    # Change a deck option
    def changeDeckOption(self, optionKey):
        option = self.options.getDeckOptions()[optionKey]
        self.options.changeDeckOption(optionKey, not option.getValue())
        self.refresh_func()
        return self.settings()

    # Change a global option
    def changeGlobalOption(self, optionKey):
        option = self.options.getGlobalOptions()[optionKey]
        self.options.changeGlobalOption(optionKey, not option.getValue())
        self.refresh_func()

    def showDescription(self, optionDesc, optionLongDesc):
        QMessageBox.information(mw, "Option: %s" % optionDesc, "%s" % optionLongDesc)
