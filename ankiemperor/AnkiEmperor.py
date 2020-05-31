from anki.hooks import wrap
from anki.collection import _Collection  # Undo
from anki.decks import DeckManager

# from anki.hooks import *
from aqt import gui_hooks, mw
from aqt.reviewer import Reviewer
from aqt.webview import AnkiWebView
from aqt.qt import (
    Qt,
    QAction,
    QDesktopWidget,
    QDialog,
    QMessageBox,
    QObjectCleanupHandler,
    QVBoxLayout,
    QDesktopServices,
    QUrl,
)

import json
from typing import Any, Dict

from .actions import HIDE, OPEN_MAIN
from .dbConnect import DBConnect
from .treasureChest import TreasureChest
from .Options import Options
from .EventManager import EventManager
from .Stats import Stats
from .World import World
from .buildingAuthority import BuildingAuthority
from .Ranks import Ranks
from .util import getPluginName
from .views.MainView import MainView
from .views.SettingsView import SettingsView


# WELCOME TO THE GOD OBJECT. YOUR JOURNEY BEGINS HERE
class AnkiEmperor(QDialog):
    def __init__(self):
        mw.addonManager.setWebExports("AnkiEmperor", ".*")

        # Setup
        self.db = DBConnect()
        self.__treasureChest = TreasureChest(self.db)
        self.__options = Options(self.db)
        self.__eventManager = EventManager(self, self.__options, self.__treasureChest)
        self.__stats = Stats(self.db, self.__eventManager)
        world = World(self.db, self.__options.getOption("activeCountry"))
        self.__buildingAuthority = BuildingAuthority(self, world)
        self.__ranks = Ranks(self.db, self.__eventManager, world)
        self.__ranks.updateRank(
            self.__treasureChest.getTotalGold(),
            self.__buildingAuthority.getActiveCountry().getCompletedObjectsPercentage(),
            True,
        )
        self.__layout = None  # Setup as a property as we must be able to clear it
        # Keep's track of current view. Useful if we want to update a view, but we're not sure which one
        self.__view = None
        self.deckSelected = False

        # Setup window
        QDialog.__init__(self, mw, Qt.WindowTitleHint)
        self.setWindowTitle(getPluginName())
        self.resize(300, 800)
        gui_hooks.reviewer_did_answer_card.append(self.answerCard)
        gui_hooks.webview_did_receive_js_message.append(self.links)
        self.open_main()

        # Wrap Anki methods

        # This should probably be handled better
        # Should each view have its own call to did_receive_js_message?
        # FIXME Investigate if there are native versions of these functions..
        _Collection.undo = wrap(_Collection.undo, self.undo)
        DeckManager.select = wrap(DeckManager.select, self.refreshSettings)

        # Add AnkiEmperor to the Anki menu
        action = QAction(getPluginName(), mw)
        action.triggered.connect(self.show)
        # mw.connect(action, SIGNAL("triggered()"), self.show)
        mw.form.menuTools.addAction(action)

    # remember how the card was answered: easy, good, ...
    def setQuality(self, quality):
        self.__lastQuality = quality

    # Gets
    def getTreasureChest(self):
        return self.__treasureChest

    def getBuildingAuthority(self):
        return self.__buildingAuthority

    def getRanks(self):
        return self.__ranks

    def getOptions(self):
        return self.__options

    def getEventManager(self):
        return self.__eventManager

    # Sets
    def setView(self, view):
        self.__view = view

    # Show window
    # Make sure AnkiEmperor shows to the right or left of Anki if possible
    def show(self):

        # Can we display it on the right?
        if (
            QDesktopWidget().width() - mw.pos().x() - mw.width() - self.width() - 50
        ) > 0:
            self.move(mw.pos().x() + mw.width() + 50, mw.pos().y() - 100)

        # Can we display it on the left?
        elif (
            QDesktopWidget().width() - mw.pos().x() + self.width() + 50
        ) < QDesktopWidget().width():
            self.move(mw.pos().x() - self.width() - 50, mw.pos().y() - 100)

        # Show window
        super(AnkiEmperor, self).show()

    # This hook makes sure that AnkiEmperor shows after Anki has loaded.
    # This lets us show AnkiEmperor in the correct position
    def onProfileLoaded(self):

        # Show window if required.
        if self.__options.getOption("openOnLaunch"):
            self.show()

    # Take gold away if card undone
    def undo(self, _Collection):
        if self.__options.getOption("pluginEnabled"):
            self.__treasureChest.undo()
            self.__buildingAuthority.undo()
            self.__stats.undo()
            self.open_main()
            self.__buildingAuthority.save()
            self.__stats.save()

    # Update AnkiEmperor when we answer a card
    def answerCard(self, Reviewer, card, ease):

        if self.__options.getOption("pluginEnabled"):
            self.setQuality(ease)
            cardsAnsweredToday = self.__stats.cardAnswered(self.__lastQuality)
            self.__stats.save()

            # Update the building process
            self.__buildingAuthority.updateBuildingProgress(
                self.__lastQuality, cardsAnsweredToday
            )
            self.__buildingAuthority.save()

            # Update rank
            self.__ranks.updateRank(
                self.__treasureChest.getTotalGold(),
                self.__buildingAuthority.getActiveCountry().getCompletedObjectsPercentage(),
                False,
            )

            # Display popup and perform event action whenever a major event has occured
            event = self.__eventManager.getNextEvent()

            if event:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.NoIcon)
                msg.setWindowTitle(getPluginName())
                msg.setText(event.performEventAndGetText())
                msg.addButton("OK", QMessageBox.AcceptRole)
                msg.exec_()

            # calculate earned gold
            self.__treasureChest.updateGold(
                card, self.__lastQuality, cardsAnsweredToday, False
            )
            self.__treasureChest.save()

            self.open_main()

    # Update the Anki Emperor Window
    def updateWindow(self, html):

        if html is None:
            return False

        # build view
        webview = AnkiWebView()
        webview.stdHtml(html)

        # Clear old layout
        if self.__layout:
            QObjectCleanupHandler().add(self.__layout)

        # build layout
        self.__layout = QVBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.addWidget(webview)

        # Update window
        self.setLayout(self.__layout)
        self.update()

    def open_main(self) -> None:
        m = MainView(
            self.deckSelected,
            self.__treasureChest,
            self.__buildingAuthority,
            self.__ranks,
            self.__options,
        )
        self.__view = m.__class__.__name__
        self.updateWindow(m.main())

    def open_settings(self) -> None:
        m = SettingsView(self.__options, self.deckSelected, self.open_settings)
        self.__view = m.__class__.__name__
        self.updateWindow(m.main())

    # Anki's pycmd syntax is kind of like React's action/reducers
    # if you squint your eyes a little bit.
    # Except, that it's really an entire API by itself
    # So, it's probably a good idea to treat it like a HTTP request, kinda.
    # So, this function is like a HTTP-request handler (with requests pre-parsed in JSON)
    # This function has to return valid JSON
    def process_request(self, request: Dict[str, Any], context: Any) -> Any:
        raise Exception("HIDE")

        def h(*_):
            raise Exception("HIDE")

        handlers = {
            OPEN_MAIN: lambda _: self._open_main(),
            HIDE: h,
        }  # lambda _: raise Exception("HIDE")} #self.hide()}
        return handlers[request["type"]](request["payload"])

    def links(self, handled, message, context):
        QMessageBox(self)
        raise Exception("HIDE")
        ret = self.process_request(json.loads(message), context)
        return (True, ret)

    # Refresh the settings if the deck is changed
    def refreshSettings(self, DeckManager, did):
        if mw.col is not None:
            self.deckSelected = True
            deck = mw.col.decks.current()
            self.__options.readDeckOptions(deck["id"])

        if self.__view.__class__.__name__ == "SettingsView":
            self.open_settings()

        # Show window if autoOpen is enabled
        if self.__options.getOption("autoOpen") and self.isHidden():
            self.show()
