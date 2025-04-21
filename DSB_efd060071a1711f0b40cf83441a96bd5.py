"""
:author: Alexander Castronovo
:organization: Max Planck Florida Institute for Neuroscience
:date: Apr 15 2025 12:37
:dragonflyVersion: 2024.1.0.1601
:UUID: efd060071a1711f0b40cf83441a96bd5
"""

__version__ = '1.0.0'

from ORSServiceClass.OrsPlugin.orsPlugin import OrsPlugin
from ORSServiceClass.OrsPlugin.uidescriptor import UIDescriptor
from ORSServiceClass.actionAndMenu.menu import Menu
from ORSServiceClass.decorators.infrastructure import menuItem


class DSB_efd060071a1711f0b40cf83441a96bd5(OrsPlugin):

    # Plugin definition
    multiple = True
    savable = False
    keepAlive = False
    canBeGenericallyOpened = False

    # UIs
    UIDescriptors = [UIDescriptor(name='MainFormDsb',
                                  title='DSB',
                                  dock='Floating',
                                  tab='Main',
                                  modal=False,
                                  collapsible=True,
                                  floatable=True)]

    def __init__(self, varname=None):
        super().__init__(varname)

    @classmethod
    def getMainFormName(cls):
        return 'MainFormDsb'

    @classmethod
    def getMainFormClass(cls):
        from .mainformdsb import MainFormDsb
        return MainFormDsb

    @classmethod
    def openGUI(cls):
        instance = DSB_efd060071a1711f0b40cf83441a96bd5()

        if instance is not None:
            instance.openWidget("MainFormDsb")

    @classmethod
    @menuItem("Plugins")
    def DSB(cls):
        menu_item = Menu(title="Start DSB",
                         id_="DSB_efd060071a1711f0b40cf83441a96bd5",
                         section="",
                         action="DSB_efd060071a1711f0b40cf83441a96bd5.openGUI()")

        return menu_item
