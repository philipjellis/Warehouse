import wx
import wx.html
from decimal import Decimal
import wx.lib.colourdb
from utilities import *

from IBPage import IndividualBenefit
from EditPage import Editor
from ExtractPage import Extractor
from ImportPage import Importer
from DatAirPage import DatAir
from SNIPage import SNI
from LCRAPage import LCRA
from DataDickPage import DataDick
import encodings

class MainFrame(wx.Frame):
    def __init__(self):
        RWtitle="Rudd and Wisdom - Participant Data Management"
        if test : RWtitle+=' P2 TEST SYSTEM'
        wx.Frame.__init__(self, None , pos=(10,10),title=RWtitle, size=(1600,950))
        self.CreateStatusBar(style=0)
#                          
        # Here we create a panel and a notebook on the panel
        p = wx.Panel(self)
        nb = wx.Notebook(p)
        
        # create the page windows as children of the notebook
        P1_IB = IndividualBenefit(nb)
        P2_Edit = Editor(nb)
        P3_Ex = Extractor(nb)
        P4_Imp = Importer(nb)
        P5_DatAir= DatAir(nb)
        P6_SNI = SNI(nb)
        P7_LCRA = LCRA(nb, self) #, self.status)
        P8_DD = DataDick(nb)
        
        #Publisher.subscribe(self.change_statusbar, 'change_statusbar')
        # add the pages to the notebook with the label to show on the tab
        nb.AddPage(P1_IB, "Home: IB, Participant Data and TaskList")
        nb.AddPage(P2_Edit, "Edit Participant Details")
        nb.AddPage(P3_Ex, "Extract Records")
        nb.AddPage(P4_Imp, "Import and Update Records")
        nb.AddPage(P5_DatAir, "Datair Conversion")
        nb.AddPage(P6_SNI, "SNI Monthly Load")
        nb.AddPage(P7_LCRA, "LCRA")
        nb.AddPage(P8_DD, "Data Dictionary")

        if test :
            bgCol =  "#FFEBCD" #LightBrown #
          #if test version then set background colour 
            P1_IB.SetBackgroundColour(bgCol)
            P2_Edit.SetBackgroundColour(bgCol)
            P3_Ex.SetBackgroundColour(bgCol)
            P4_Imp.SetBackgroundColour(bgCol)
            P5_DatAir.SetBackgroundColour(bgCol)
            P6_SNI.SetBackgroundColour(bgCol)
            P7_LCRA.SetBackgroundColour(bgCol)
            P8_DD.SetBackgroundColour(bgCol)
        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        p.SetSizerAndFit(sizer)

    def change_statusbar(self, m):
        self.SetStatusText(m)

if __name__ == "__main__":
    app = wx.App(False)
    MainFrame().Show()
    app.MainLoop()
