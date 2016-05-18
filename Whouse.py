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
from NACOPage import Naco
from DataDickPage import DataDick
import encodings
from pubsub import pub

class MainFrame(wx.Frame):
    def __init__(self):
        RWtitle="Rudd and Wisdom - Participant Data Management"
        if test : RWtitle+=' P2 TEST SYSTEM'
        wx.Frame.__init__(self, None , pos=(10,10),title=RWtitle, size=(1600,950))
        self.CreateStatusBar(style=0)
#                          
        # Here we create a panel and a notebook on the panel
        self.p = wx.Panel(self)
        nb = wx.Notebook(self.p)
        
        # create the page windows as children of the notebook
        self.P1_IB = IndividualBenefit(nb)
        self.P2_Edit = Editor(nb)
        self.P3_Ex = Extractor(nb)
        self.P4_Imp = Importer(nb)
        self.P5_DatAir= DatAir(nb)
        self.P6_SNI = SNI(nb)
        self.P7_LCRA = LCRA(nb, self) #, self.status)
	self.P8_NACO = Naco(nb, self)
        self.P9_DD = DataDick(nb)
        
        #Publisher.subscribe(self.change_statusbar, 'change_statusbar')
        # add the pages to the notebook with the label to show on the tab
        nb.AddPage(self.P1_IB, "Home: IB, Participant Data and TaskList")
        nb.AddPage(self.P2_Edit, "Edit Participant Details")
        nb.AddPage(self.P3_Ex, "Extract Records")
        nb.AddPage(self.P4_Imp, "Import and Update Records")
        nb.AddPage(self.P5_DatAir, "Datair Conversion")
        nb.AddPage(self.P6_SNI, "SNI Monthly Load")
        nb.AddPage(self.P7_LCRA, "LCRA")
	nb.AddPage(self.P8_NACO, "Naco")
        nb.AddPage(self.P9_DD, "Data Dictionary")

        pub.subscribe(self.listener2,'Production')
        pub.sendMessage('Production',arg1='Prod')

        #self.setbg(self.Production)
        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        self.p.SetSizerAndFit(sizer)

    def listener2(self,arg1):
	#print 'listener 2 got ',arg1
	#prod_flag = arg1
        self.setbg(arg1)	

    def setbg(self,prod_flag):
	if prod_flag == 'Prod':
	    bgCol = "#F0F0F0"
	else:
	    bgCol = "#FFEBCD"
        self.P1_IB.SetBackgroundColour(bgCol)
        self.P2_Edit.SetBackgroundColour(bgCol)
        self.P3_Ex.SetBackgroundColour(bgCol)
        self.P4_Imp.SetBackgroundColour(bgCol)
        #self.P5_DatAir.SetBackgroundColour(bgCol)
        #self.P6_SNI.SetBackgroundColour(bgCol)
        #self.P7_LCRA.SetBackgroundColour(bgCol)
	self.P8_NACO.SetBackgroundColour(bgCol)
        #self.P9_DD.SetBackgroundColour(bgCol)
	self.p.Refresh()

    def change_statusbar(self, m):
        self.SetStatusText(m)

if __name__ == "__main__":
    app = wx.App(False)
    MainFrame().Show()
    app.MainLoop()
