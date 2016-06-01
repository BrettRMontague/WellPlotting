import os
import re
import sys
import warnings

import numpy as np
import pandas as pd
from PySide import *
from PySide import QtGui
from PySide.QtCore import *
from PySide.QtCore import QUrl
from PySide.QtGui import *
from PySide.QtWebKit import QWebView

# TODO: CLEAN OUTLIERS ON A PER 50m basis! Clone the dataframe and step through them.  over a range!  Interpolate
# TODO: MULTI WELL PAD SETUP
# TODO: All of the trig and extrap methods.
# TODO: GEOGRAPHIC COORDINATES: Take Surface and surveys, convert to Lat/Long and plot each discrete point?
# TODO: MAKE SURE SUBSEA ON TVD PLOTS IS CENTERED
# TODO: Fix TVD miniplots where only change of inc is between two survey points

# TODO: When done testing, uncomment file dialogs and confirm KB function

warnings.simplefilter(action="ignore", category=RuntimeWarning)


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        # title of the window
        self.setWindowTitle('Well Plotter v0.5 Alpha')
        # fix window size
        self.setFixedSize(600, 270)
        # status bar with initial message
        self.statusBar().showMessage('Ready to plot')
        self.setWindowIcon(QtGui.QIcon('oilrig.png'))

        # Layout
        cWidget = QtGui.QWidget(self)
        grid = QtGui.QGridLayout(cWidget)
        grid.setSpacing(2)

        quitAction = QtGui.QAction("Exit", self)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.setStatusTip('Quit the Application')
        quitAction.triggered.connect(self.close_application)

        self.statusBar()

        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        aboutMenu = mainMenu.addMenu('&About')
        fileMenu.addAction(quitAction)
        # aboutMenu.addAction(self.testWindow)


        Button_input1 = QtGui.QPushButton("Import Surveys")
        grid.addWidget(Button_input1, 0, 0)
        Button_input1.clicked.connect(self.importSurveys)
        surveysPathBox = self.survTextBox = QtGui.QTextEdit(self)

        Button_input2 = QtGui.QPushButton("Import Gamma")
        grid.addWidget(Button_input2, 1, 0)
        Button_input2.clicked.connect(self.importGamma)
        gammaPathBox = self.gammaTextBox = QtGui.QTextEdit(self)

        Button_input3 = QtGui.QPushButton("Import ROP and Gas")
        grid.addWidget(Button_input3, 2, 0)
        Button_input3.clicked.connect(self.importROPandGas)
        ropPathBox = self.ropTextBox = QtGui.QTextEdit(self)

        Button_input4 = QtGui.QPushButton("Generate WellPlot")
        grid.addWidget(Button_input4, 3, 0)
        Button_input4.clicked.connect(self.plotWell)

        Button_input5 = QtGui.QPushButton("Plot Vert. TVD Slices")
        grid.addWidget(Button_input5, 4, 0)
        Button_input5.clicked.connect(self.plotInflections)

        Button_input6 = QtGui.QPushButton("Plot to Google Maps")
        grid.addWidget(Button_input6, 5, 0)
        Button_input6.clicked.connect(self.googlePlot)

        Button_input7 = QtGui.QPushButton("Write to Excel")
        grid.addWidget(Button_input7, 6, 0)
        Button_input7.clicked.connect(self.writeSpreadsheet)

        Button_input8 = QtGui.QPushButton("Quick TVD Estimation")
        grid.addWidget(Button_input8, 7, 0)
        Button_input8.clicked.connect(self.quickTVD)

        grid.addWidget(surveysPathBox, 0, 1)
        grid.addWidget(gammaPathBox, 1, 1)
        grid.addWidget(ropPathBox, 2, 1)

        self.setCentralWidget(cWidget)

    def importSurveys(self):
        global fileName2

        # fileName2tup = QtGui.QFileDialog.getOpenFileName(self, "Open Survey File (.txt)", '',
        #                                                  "TXT Files (*.txt *.TXT)")
        # fileName2 = fileName2tup[0]

        fileName2 = 'C:/Users/Brett/Desktop/Wellplotting/TD Surveys.TXT'

        self.survTextBox.setText(fileName2)

        surveyFile = open(fileName2, 'r')

        os.chdir((os.path.dirname(fileName2)))

        # Find the header line number in survey file
        lookup = 'Measured'
        with open(fileName2) as myFile:
            for num, line in enumerate(myFile, 1):
                if lookup in line:
                    surveySkipRows = int(num)
                    break

        surveyText = surveyFile.read()
        rkbRegex = re.compile(r'(RKB:\s)((\d)?(\d)?(\d)?(\d)?\d.\d(\d)?)')
        rkbRegexResult = rkbRegex.search(surveyText)
        global KB
        KB = float(rkbRegexResult.group(2))
        surveyFile.seek(0)
        # Make a pandas dataframe for Survey file
        global readSurveyData
        readSurveyData = pd.read_csv(surveyFile, sep='\s+', error_bad_lines=False, tupleize_cols=True,
                                     skiprows=surveySkipRows,
                                     header=[0, 1])
        # --Close the Survey File--
        surveyFile.close()
        readSurveyData = readSurveyData.apply(pd.to_numeric, errors='coerce')
        readSurveyData = readSurveyData.dropna()
        readSurveyData = readSurveyData.reset_index(drop=True)

        # def confirmSurvey(self):
        #     global KB
        #     choice = QtGui.QMessageBox.question(self, 'Confirm KB',
        #                                         "Is " + str(KB) + "m the correct KB for this well?",
        #                                         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        #     if choice == QtGui.QMessageBox.Yes:
        #         msg = QtGui.QMessageBox()
        #         msg.setIcon(QtGui.QMessageBox.Information)
        #
        #         msg.setText('The KB has been set to: ' + str(KB) + "m")
        #         msg.setWindowTitle("KB Updated.")
        #         msg.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        #
        #
        #
        #     else:
        #         uKB = QtGui.QInputDialog.getDouble(self, 'Update KB', 'Please enter the correct KB for this well.')
        #         KB = float(uKB[0])
        #
        # confirmSurvey(self)

        readSurveyData[('Subsea', 'Meters')] = float(KB) - readSurveyData[('Vertical', 'Depth')]

        self.statusBar().showMessage('Surveys Imported')

    def importGamma(self):
        # --GAMMA FILE--
        # Initialize QT dialog for gamma file
        global fileName
        # fileNametup = QtGui.QFileDialog.getOpenFileName(self, "Open Gamma File (.las)", '',
        #                                                 "LAS Files (*.las *.LAS)")
        # fileName = fileNametup[0]

        fileName = 'C:/Users/Brett/Desktop/Wellplotting/TD Gamma.las'

        self.gammaTextBox.setText(fileName)
        # Find the header line number in gamma file
        lookup = '~A'
        with open(fileName) as myFile:
            for num, line in enumerate(myFile, 1):
                if lookup in line:
                    gammaSkipRows = int(num + 2)
                    # Make a pandas Dataframe for Gamma
        gammaFile = open(fileName, 'r')
        global readGammaData
        readGammaData = pd.read_csv(gammaFile, sep='\s+', skiprows=gammaSkipRows, na_values=['-999.25'],
                                    names=['MD', 'Gamma', 'TVD'])
        # --Close the Gamma File.--
        gammaFile.close()

        self.statusBar().showMessage('Gamma Imported')

    def importROPandGas(self):
        global fileName3
        # Initialize Qt dialog for Gas/ROP file PASON!

        # fileName3tup = QtGui.QFileDialog.getOpenFileName(self, "Import Pason Gas/ROP File (.txt)", '',
        #                                                  "Pason Gas and ROP Files (*.txt *.TXT)")
        # fileName3 = fileName3tup[0]

        fileName3 = 'C:/Users/Brett/Desktop/Wellplotting/TD Gas and ROP.txt'
        gasandropFile = open(fileName3, 'r')

        self.ropTextBox.setText(fileName3)
        # Make a pandas dataframe for Gas/ROP file
        global readGasData
        readGasData = pd.read_csv(gasandropFile, usecols=range(3), skiprows=20, sep='\s+', na_values=['-999.25', '--'],
                                  names=['MD', 'ROP', 'Gas'])
        gasandropFile.close()
        # --Close the Gas/ROP File--

        self.statusBar().showMessage('Gas and ROP Imported')

    def plotWell(self):
        from bokeh.models import LinearAxis, Range1d, HoverTool, CrosshairTool
        from bokeh.plotting import figure, output_file, vplot
        # Print the KB, Standard Dev, Median
        print('The KB is: ' + str(KB))
        print('ROP Standard dev is ' + str(readGasData['ROP'].std()))
        print('ROP median is ' + str(readGasData['ROP'].median()))

        # TODO:  Look at a better way to do this, rolling median or something...
        mask = (abs(readGasData['ROP'] - readGasData['ROP'].median()) > readGasData['ROP'].median() * 3)

        readGasROPCol = readGasData['ROP']

        readGasROPCol[mask] = readGasROPCol.median()

        ropMean = np.nanmean(readGasData['ROP'])

        # print('ROP mean is ' + str(ropMean))

        # Get Gamma and ROP Standard dev

        gammaSTD = np.nanstd(readGammaData['Gamma'])

        gasplotYRangeEnd = readGasData['Gas'].max()
        # print(gasplotYRangeEnd)

        # Set End of Y Range as TD Subsea _10
        plotYRangeEnd = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) + 10)
        # Set Start of Y Range as TD Subsea -10
        plotYRangeStart = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) - 10)

        # Find the values where the well builds > 75 degrees as the start of the X Range
        plotXRangeStartCalc = (readSurveyData[('Angle', 'Deg')].where(readSurveyData[('Angle', 'Deg')] > 70))
        # Grab the index of the first value after 75 degrees
        plotXRangeStartIndex = plotXRangeStartCalc.first_valid_index()
        # Set the plotXRangeStart variable as the first MD value after 75 degrees
        plotXRangeStart = (readSurveyData[('Depth', 'Meters')].ix[plotXRangeStartIndex])

        # Set End of X Range as TD MD + 20
        plotXRangeEnd = ((readSurveyData[('Depth', 'Meters')].iloc[-1]) + 20)

        plotx1 = readSurveyData[('Depth', 'Meters')]
        ploty1 = readSurveyData[('Subsea', 'Meters')]
        # set the second series: Gamma MD Depths on X, Gamma counts on Y
        plotx2 = readGammaData['MD']
        ploty2 = readGammaData['Gamma']

        hover = HoverTool(tooltips=[("(MD, Value)", "(@x{1.11}, @y{1.11})"), ], mode='vline')
        hover2 = HoverTool(tooltips=[("(MD, Value)", "(@x{1.11}, @y{1.11})"), ], mode='vline')
        crosshair = CrosshairTool(dimensions=(['height', 'y']))
        crosshair2 = CrosshairTool(dimensions=(['height', 'y']))
        # Wellpath and gamma plot

        wellPlot = figure(width=1280, height=420, x_range=(plotXRangeStart, plotXRangeEnd),
                          y_range=(plotYRangeStart, plotYRangeEnd), min_border=80,
                          tools=[hover, crosshair2, "pan,wheel_zoom,box_zoom,reset,previewsave"])
        wellPlot.line(plotx1, ploty1, line_color="black", legend='Well Path')
        wellPlot.circle(plotx1, ploty1, fill_color='red', size=5, legend='Well Path')

        wellPlot.xaxis.axis_label = "Measured Depth (m)"
        wellPlot.yaxis.axis_label = "Subsea (m)"

        wellPlot.xaxis.axis_label_text_font_size = '12pt'
        wellPlot.yaxis.axis_label_text_font_size = '12pt'
        wellPlot.ygrid.minor_grid_line_color = 'grey'
        wellPlot.ygrid.grid_line_color = 'grey'

        wellPlot.extra_y_ranges['foo'] = Range1d(0, 250)
        wellPlot.line(plotx2, ploty2, line_color="blue", y_range_name="foo", legend='Gamma')

        wellPlot.add_layout(LinearAxis(y_range_name="foo"), 'right')
        wellPlot.yaxis

        plotx3 = readGasData['MD']
        ploty3 = readGasData['Gas']
        ploty4 = readGasROPCol

        wellPlotGasROP = figure(width=1280, height=300, x_range=(plotXRangeStart, plotXRangeEnd),
                                y_range=(0, gasplotYRangeEnd),
                                min_border=80,
                                tools=[hover2, crosshair, "pan,wheel_zoom,box_zoom,reset, previewsave"])
        # wellPlotGasROP.toolbar_location = None
        wellPlotGasROP.line(plotx3, ploty3, line_color="red", legend='Total Gas')
        wellPlotGasROP.extra_y_ranges['foo'] = Range1d(0, 5)
        wellPlotGasROP.line(plotx3, ploty4, line_color="blue", y_range_name="foo", legend='ROP')
        wellPlotGasROP.add_layout(LinearAxis(y_range_name="foo"), 'right')

        wellPlotGasROP.xaxis.axis_label = "Measured Depth (m)"
        wellPlotGasROP.yaxis.axis_label = "Subsea (m)"

        wellPlotGasROP.xaxis.axis_label_text_font_size = '12pt'
        wellPlotGasROP.yaxis.axis_label_text_font_size = '12pt'
        wellPlotGasROP.ygrid.grid_line_color = 'grey'

        wellPlots = vplot(wellPlot, wellPlotGasROP)

        output_file("Wellplot.html", title="Wellplot")

        self.win = QWebView()
        self.win.showMaximized()
        self.win.load(QUrl('Wellplot.html'))
        self.win.show()

        # show(wellPlots)

        self.statusBar().showMessage('Well Plotted')

    def googlePlot(self):
        import gmplot
        import webbrowser
        new = 2
        mymap = gmplot.GoogleMapPlotter(51.19705, -108.5576, 16)
        # mymap = GoogleMapPlotter.from_geocode("Stanford University")

        # mymap.grid(37.42, 37.43, 0.001, -122.15, -122.14, 0.001)
        # mymap.marker(37.427, -122.145, "yellow")
        # mymap.marker(37.428, -122.146, "cornflowerblue")
        # mymap.marker(37.429, -122.144, "k")
        # lat, lng = mymap.geocode("Stanford University")
        # mymap.marker(lat, lng, "red")
        # mymap.circle(37.429, -122.145, 100, "#FF0000", ew=2)
        path = [(51.19705, 51.199623, 51.204336), (-108.5576, -108.554936, -108.554927)]
        # scatter_path = [(51.19705, 51.199623, 51.204336), (-108.5576, -108.554936, -108.554927)]
        # path2 = [[i+.01 for i in path[0]], [i+.02 for i in path[1]]]
        # path3 = [(37.433302 , 37.431257 , 37.427644 , 37.430303), (-122.14488, -122.133121, -122.137799, -122.148743)]
        # path4 = [(37.423074, 37.422700, 37.422410, 37.422188, 37.422274, 37.422495, 37.422962, 37.423552, 37.424387, 37.425920, 37.425937),
        #      (-122.150288, -122.149794, -122.148936, -122.148142, -122.146747, -122.14561, -122.144773, -122.143936, -122.142992, -122.147863, -122.145953)]
        mymap.plot(path[0], path[1], "red", edge_width=2)
        # mymap.plot(path2[0], path2[1], "red")
        # mymap.polygon(path3[0], path3[1], edge_color="cyan", edge_width=5, face_color="blue", face_alpha=0.1)
        # mymap.heatmap(path[0], path[1], threshold=10, radius=40)
        # mymap.heatmap(path3[0], path3[1], threshold=10, radius=40, dissipating=False, gradient=[(30,30,30,0), (30,30,30,1), (50, 50, 50, 1)])
        # mymap.scatter(path[0], path[1], c='r', marker=True)
        # mymap.scatter(path[0], path[1], s=90, marker=False, alpha=0.1)
        # mymap.marker(51.19705, -108.5576, color='FF0000')
        # Get more points with:
        # http://www.findlatitudeandlongitude.com/click-lat-lng-list/
        # scatter_path = ([37.424435, 37.424417, 37.424417, 37.424554, 37.424775, 37.425099, 37.425235, 37.425082, 37.424656, 37.423957, 37.422952, 37.421759, 37.420447, 37.419135, 37.417822, 37.417209],
        #                 [-122.142048, -122.141275, -122.140503, -122.139688, -122.138872, -122.138078, -122.137241, -122.136405, -122.135568, -122.134731, -122.133894, -122.133057, -122.13222, -122.131383, -122.130557, -122.129999])
        # mymap.scatter(scatter_path[0], scatter_path[1], c='r', marker=True)
        mymap.draw('mymap.html')
        webbrowser.open('mymap.html', new=new)

    def writeSpreadsheet(self):
        writer = pd.ExcelWriter('WellSheet.xlsx', engine='xlsxwriter')
        readSurveyData.to_excel(writer, 'Survey')
        readGasData.to_excel(writer, 'GasROP')
        readGammaData.to_excel(writer, 'Gamma')
        writer.save()

    def plotInflections(self):
        from itertools import groupby
        from operator import itemgetter
        from bokeh.plotting import figure, show, output_file, gridplot

        # Create a copy of the survey dataframe
        inflectionFrame = readSurveyData.copy(deep=True)

        # Normalize the inclination to + is up - is down
        inflectionFrame[('Angle', 'Deg')] = inflectionFrame[('Angle', 'Deg')] - 90

        # fetch the indexes where inclination is going up
        posinflectionFrame = (inflectionFrame.where(inflectionFrame[('Angle', 'Deg')] > 0))
        posinflectionFrame = posinflectionFrame.dropna()
        posindexesList = posinflectionFrame.index.tolist()

        # fetch the indexes where the inclination is going down.
        neginflectionFrame = (inflectionFrame.where(inflectionFrame[('Angle', 'Deg')] < 0))
        neginflectionFrame = neginflectionFrame.dropna()
        negindexesList = neginflectionFrame.index.tolist()

        poschunksList = []

        for k, g in groupby(enumerate(posindexesList), lambda ix: ix[0] - ix[1]):
            poschunksList.append(list(map(itemgetter(1), g)))

        negchunksList = []

        for k, g in groupby(enumerate(negindexesList), lambda ix: ix[0] - ix[1]):
            negchunksList.append(list(map(itemgetter(1), g)))

        # print(posinflectionFrame)
        # print(posinflectionFrame.iloc[1])

        posrangeList = []
        for item in poschunksList:
            if inflectionFrame[('Depth', 'Meters')].iloc[item[0]] != inflectionFrame[('Depth', 'Meters')].iloc[
                item[-1]]:
                posrangeList.append(((int(inflectionFrame[('Depth', 'Meters')].iloc[item[0]])),
                                     (int(inflectionFrame[('Depth', 'Meters')].iloc[item[-1]]))))

        negrangeList = []
        for item in negchunksList:
            if inflectionFrame[('Depth', 'Meters')].iloc[item[0]] != inflectionFrame[('Depth', 'Meters')].iloc[
                item[-1]]:
                negrangeList.append(((int(inflectionFrame[('Depth', 'Meters')].iloc[item[0]])),
                                     (int(inflectionFrame[('Depth', 'Meters')].iloc[item[-1]]))))

        # Set end of Y Range as TD Subsea +2
        plotYRangeInflecStart = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) + 2)
        # Set Start of Y Range as TD Subsea -2
        plotYRangeInflecEnd = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) - 2)

        # Create list vars for finding and iterating through climbing TVD Gamma Slices
        posPlots = []
        posPlotsGamma = []
        posPlotsSubSea = []
        # Create list vars for finding and iterating through dropping TVD Gamma Slices
        negPlots = []
        negPlotsGamma = []
        negPlotsSubSea = []

        # Lists for combined/allin one plot
        # bothPlotsGamma = []
        # bothPlotsSubSea = []

        # Create list vars for creating MD miniplots climbing TVD Slices
        posPlotsMD = []
        posPlotsMDSlicesMD = []
        posPlotsMDSlicesSS = []

        # Create list vars for creating MD miniplots diving TVD Slices
        negPlotsMD = []
        negPlotsMDSlicesMD = []
        negPlotsMDSlicesSS = []

        # Positive MD Slice Code
        for k, v in posrangeList:
            posMDSlices = readSurveyData[
                (readSurveyData[('Depth', 'Meters')] > k) & (readSurveyData[('Depth', 'Meters')] < v)]
            posMDSlices = posMDSlices.dropna()
            p = {
                "plotx2": posMDSlices[('Depth', 'Meters')],
                "ploty2": posMDSlices[('Subsea', 'Meters')]
            }
            posPlotsMD.append(p)
            posPlotsMDSlicesMD.append(posMDSlices[('Depth', 'Meters')])
            posPlotsMDSlicesSS.append(posMDSlices[('Subsea', 'Meters')])

        # Negative MD Slice Code
        for k, v in negrangeList:
            negMDSlices = readSurveyData[
                (readSurveyData[('Depth', 'Meters')] > k) & (readSurveyData[('Depth', 'Meters')] < v)]
            negMDSlices = negMDSlices.dropna()
            p = {
                "plotx2": negMDSlices[('Depth', 'Meters')],
                "ploty2": negMDSlices[('Subsea', 'Meters')]
            }
            negPlotsMD.append(p)
            negPlotsMDSlicesMD.append(negMDSlices[('Depth', 'Meters')])
            negPlotsMDSlicesSS.append(negMDSlices[('Subsea', 'Meters')])

        # Positive (Climbing) TVD Gamma Slices code
        for k, v in posrangeList:
            posGammaFrame = readGammaData[(readGammaData.MD > k) & (readGammaData.MD < v)]
            posGammaFrame = posGammaFrame.dropna()
            posGammaFrame['SubSea'] = float(KB) - posGammaFrame['TVD']
            p = {
                "plotx1": posGammaFrame['Gamma'],
                "ploty1": posGammaFrame['SubSea']
            }
            posPlots.append(p)
            posPlotsGamma.append(posGammaFrame['Gamma'])
            posPlotsSubSea.append(posGammaFrame['SubSea'])
            # Code for combined plots
            # bothPlotsGamma.append(posGammaFrame['Gamma'])
            # bothPlotsSubSea.append(posGammaFrame['SubSea'])

        # Negative (Dropping) TVD Gamma Slices code
        for k, v in negrangeList:
            negGammaFrame = readGammaData[(readGammaData.MD > k) & (readGammaData.MD < v)]
            negGammaFrame = negGammaFrame.dropna()
            negGammaFrame['SubSea'] = float(KB) - negGammaFrame['TVD']
            p = {
                "plotx1": negGammaFrame['Gamma'],
                "ploty1": negGammaFrame['SubSea']
            }
            negPlots.append(p)
            negPlotsGamma.append(negGammaFrame['Gamma'])
            negPlotsSubSea.append(negGammaFrame['SubSea'])
            # Code for combined plots
            # bothPlotsGamma.append(negGammaFrame['Gamma'])
            # bothPlotsSubSea.append(negGammaFrame['SubSea'])

        # Set End of Y Range as TD Subsea _10
        plotYRangeEnd = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) + 10)
        # Set Start of Y Range as TD Subsea -10
        plotYRangeStart = ((readSurveyData[('Subsea', 'Meters')].iloc[-1]) - 10)

        # Find the values where the well builds > 75 degrees as the start of the X Range
        plotXRangeStartCalc = (readSurveyData[('Angle', 'Deg')].where(readSurveyData[('Angle', 'Deg')] > 70))
        # Grab the index of the first value after 75 degrees
        plotXRangeStartIndex = plotXRangeStartCalc.first_valid_index()
        # Set the plotXRangeStart variable as the first MD value after 75 degrees
        plotXRangeStart = (readSurveyData[('Depth', 'Meters')].ix[plotXRangeStartIndex])

        # Set End of X Range as TD MD + 20
        plotXRangeEnd = ((readSurveyData[('Depth', 'Meters')].iloc[-1]) + 20)

        # Create x and Y axes for under TVD Gamma miniplots
        plotx3 = readSurveyData[('Depth', 'Meters')]
        ploty3 = readSurveyData[('Subsea', 'Meters')]

        # Positive Grid Plot Code
        # Create and plot positive TVD slices
        postvdPlotter = []
        for i, plot in enumerate(posPlots):
            plotTitle = (str(posrangeList[i][0]) + 'mMD' + ' to ' + str(posrangeList[i][1]) + 'mMD')
            postvdPlot = figure(width=400, height=400, x_range=(0, 150),
                                y_range=(plotYRangeInflecEnd, plotYRangeInflecStart),
                                title=plotTitle, min_border=10, tools="pan,wheel_zoom,box_zoom,reset,previewsave")
            plotx1 = posPlots[i]['plotx1']
            ploty1 = posPlots[i]['ploty1']
            postvdPlot.xaxis.axis_label = "Gamma (CPS)"
            postvdPlot.yaxis.axis_label = "Subsea (m)"
            postvdPlot.title_text_font_size = '16pt'
            postvdPlot.xaxis.axis_label_text_font_size = '12pt'
            postvdPlot.yaxis.axis_label_text_font_size = '12pt'
            postvdPlot.line(plotx1, ploty1, line_width=1, line_color="green")
            postvdPlotter.append(postvdPlot)

        # Create and plot Positive MD miniplot slices.
        posMDPlotter = []
        for i, plot in enumerate(posPlotsMD):
            posMDPlot = figure(width=400, height=225, x_range=(plotXRangeStart, plotXRangeEnd),
                               y_range=(plotYRangeStart, plotYRangeEnd),
                               min_border=10, tools="pan,wheel_zoom,box_zoom,reset,previewsave")
            plotx2 = posPlotsMD[i]['plotx2']
            ploty2 = posPlotsMD[i]['ploty2']
            posMDPlot.xaxis.axis_label = "Measured Depth (m)"
            posMDPlot.yaxis.axis_label = "Subsea (m)"
            posMDPlot.xaxis.axis_label_text_font_size = '10pt'
            posMDPlot.yaxis.axis_label_text_font_size = '10pt'
            posMDPlot.line(plotx3, ploty3, line_dash=[4, 4], line_width=1, line_color="grey")
            posMDPlot.line(plotx2, ploty2, line_width=3, line_color="red")

            posMDPlotter.append(posMDPlot)

        plotfilename = ("TVD_Up.html")
        output_file(plotfilename, title="TVD Plot Climbing")

        grid = gridplot([postvdPlotter, posMDPlotter])

        # self.win = QWebView()
        # self.win.showMaximized()
        # self.win.load(QUrl('TVD_Up.html'))
        # self.win.show()

        show(grid)

        # Negative Grid Plot Code
        # Create and plot Negative TVD slices.
        negtvdPlotter = []
        for i, plot in enumerate(negPlots):
            plotTitle = (str(negrangeList[i][0]) + 'mMD' + ' to ' + str(negrangeList[i][1]) + 'mMD')
            negtvdPlot = figure(width=400, height=400, x_range=(0, 150),
                                y_range=(plotYRangeInflecEnd, plotYRangeInflecStart),
                                title=plotTitle, min_border=10,
                                tools="pan,wheel_zoom,box_zoom,reset,previewsave")
            plotx1 = negPlots[i]['plotx1']
            ploty1 = negPlots[i]['ploty1']
            negtvdPlot.xaxis.axis_label = "Gamma (CPS)"
            negtvdPlot.yaxis.axis_label = "Subsea (m)"
            negtvdPlot.title_text_font_size = '16pt'
            negtvdPlot.xaxis.axis_label_text_font_size = '12pt'
            negtvdPlot.yaxis.axis_label_text_font_size = '12pt'
            negtvdPlot.line(plotx1, ploty1, line_width=1, line_color="green")
            negtvdPlotter.append(negtvdPlot)

        # Create and plot Negative MD miniplot slices.
        negMDPlotter = []
        for i, plot in enumerate(negPlotsMD):
            negMDPlot = figure(width=400, height=225, x_range=(plotXRangeStart, plotXRangeEnd),
                               y_range=(plotYRangeStart, plotYRangeEnd),
                               min_border=10, tools="pan,wheel_zoom,box_zoom,reset,previewsave")
            plotx2 = negPlotsMD[i]['plotx2']
            ploty2 = negPlotsMD[i]['ploty2']
            negMDPlot.line(plotx3, ploty3, line_dash=[4, 4], line_width=1, line_color="grey")
            negMDPlot.line(plotx2, ploty2, line_width=3, line_color="red")
            negMDPlot.xaxis.axis_label = "Measured Depth (m)"
            negMDPlot.yaxis.axis_label = "Subsea (m)"
            negMDPlot.xaxis.axis_label_text_font_size = '10pt'
            negMDPlot.yaxis.axis_label_text_font_size = '10pt'
            negMDPlotter.append(negMDPlot)

        plotfilename = ("TVD_Down.html")
        output_file(plotfilename, title="TVD Plot Diving")
        grid2 = gridplot([negtvdPlotter, negMDPlotter])

        # self.win2 = QWebView()
        # self.win2.showMaximized()
        # self.win2.load(QUrl('TVD_Down.html'))
        # self.win2.show()

        show(grid2)

        # #MULTI LINE CODE
        # print(len(bothPlotsGamma))
        # print(len(bothPlotsSubSea))
        # tvdPlot = figure(width=500, height=500, x_range=(0, 150), y_range=(plotYRangeEnd, plotYRangeStart), min_border=80)
        # #tvdPlot.multi_line(xs=posPlotsGamma, ys=posPlotsSubSea, color=['red','green','blue','aqua', 'brown', 'crimson'])
        # tvdPlot.multi_line(xs=bothPlotsGamma, ys=bothPlotsSubSea, color=['red','green','blue','aqua', 'brown', 'crimson', 'DarkSalmon', 'DarkViolet', 'DarkTurquoise'])
        # plotfilename = ("TVDMultiplot.html")
        # output_file(plotfilename, title="TVD Plot")
        # show(tvdPlot)

    def close_application(self):
        sys.exit()

    def quickTVD(self):

        # TVDNum = 0

        def blah():
            TVD = float(le.text())
            MD = float(le2.text())
            INC = float(le3.text())

            print('TVD is ' + str(TVD) + ' MD is ' + str(MD) + ' INC is ' + str(INC))

        def getTVDint():
            TVDNum, ok = QInputDialog.getInt(self, "integer input dialog", "enter a number")

            if ok:
                le.setText(str(TVDNum))

        def getMDint():
            num, ok = QInputDialog.getInt(self, "integer input dialog", "enter a number")

            if ok:
                le2.setText(str(num))

        def getIncint():
            num, ok = QInputDialog.getInt(self, "integer input dialog", "enter a number")

            if ok:
                le3.setText(str(num))

        self.wid = QtGui.QWidget()
        self.wid.resize(500, 300)
        self.wid.setWindowTitle('TVD Extrapolation')
        self.wid.setWindowIcon(QtGui.QIcon('oilrig.png'))
        self.wid.show()


        grid = QtGui.QGridLayout(self.wid)


        le = QLineEdit()
        le2 = QLineEdit()
        le3 = QLineEdit()
        le4 = QLineEdit()

        Button_input1 = QtGui.QPushButton("Enter TVD")
        grid.addWidget(Button_input1, 1, 0)
        grid.addWidget(le, 1, 1)
        Button_input1.clicked.connect(getTVDint)

        Button_input2 = QtGui.QPushButton("Enter MD")
        grid.addWidget(Button_input2, 2, 0)
        grid.addWidget(le2, 2, 1)
        Button_input2.clicked.connect(getMDint)

        Button_input3 = QtGui.QPushButton("Enter INC")
        grid.addWidget(Button_input3, 3, 0)
        grid.addWidget(le3, 3, 1)
        Button_input3.clicked.connect(getIncint)

        Button_input4 = QtGui.QPushButton("Extrapolate")
        grid.addWidget(Button_input4, 4, 0)
        grid.addWidget(le4, 4, 1)
        Button_input4.clicked.connect(blah)


def main():
    app = QtGui.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


main()
