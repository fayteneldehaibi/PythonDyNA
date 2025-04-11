# -*- coding: utf-8 -*-
'''
DyNA: Dynamic Network Analysis
Translated into Python by Fayten El-Dehaibi
Python file created 13 Dec 2024
'''

import sys
import os
import PyQt5
import matplotlib
from PyQt5 import QtCore, QtGui, QtWidgets
import openpyxl
import numpy
import pandas
import scipy
from scipy import stats
import xlsxwriter
import networkx as nx
import matplotlib.pyplot as plt

app = QtWidgets.QApplication(sys.argv)

class Form(QtWidgets.QDialog):
    def __init__(self, parent = None):
        super(Form, self).__init__(parent)

        titleBox = QtWidgets.QLineEdit('Title')
        titleBox.selectAll()
        fileButton = QtWidgets.QPushButton('...')
        fileLine = QtWidgets.QLineEdit()
        fileLine.setReadOnly(True)
        sheetLine = QtWidgets.QLineEdit('Sheet1')
        #number of time points #Automatically detected from file? Ask Ruben
        intervalLine = QtWidgets.QLineEdit('2')
        intervalLine.setValidator(QtGui.QIntValidator(1,9999))
        nodeColorRainbow = QtWidgets.QRadioButton('Colorful Connected Nodes')
        nodeColorRed = QtWidgets.QRadioButton('Red Connected Nodes')
        nodeColorRainbow.setChecked(True)

        ctlBox = QtWidgets.QGroupBox('Add Control Group')
        ctlBox.setCheckable(True)
        ctlBox.setChecked(False)
        ctlFileButton = QtWidgets.QPushButton('...')
        ctlFileLine = QtWidgets.QLineEdit()
        ctlFileLine.setReadOnly(True)
        ctlSheetLine = QtWidgets.QLineEdit('Sheet1')
        ctlLO = QtWidgets.QVBoxLayout()
        ctlFileLO = QtWidgets.QHBoxLayout()
        ctlFileLO.addWidget(QtWidgets.QLabel('Control File:'))
        ctlFileLO.addWidget(ctlFileLine)
        ctlFileLO.addWidget(ctlFileButton)
        ctlLO.addLayout(ctlFileLO)
        ctlSheetLO = QtWidgets.QHBoxLayout()
        ctlSheetLO.addWidget(QtWidgets.QLabel('Sheet:'))
        ctlSheetLO.addWidget(ctlSheetLine)
        ctlLO.addLayout(ctlSheetLO)
        ctlBox.setLayout(ctlLO)
        corrThreshLine = QtWidgets.QDoubleSpinBox()
        corrThreshLine.setMinimum(0)
        corrThreshLine.setMaximum(1)
        corrThreshLine.setValue(0.95)
        runButton = QtWidgets.QPushButton('Run DyNA')
        batchButton = QtWidgets.QPushButton('Run DyNA Batch')
        batchButton.setToolTip('Runs DyNA from 0.7-0.95 stringency')

        totalLayout = QtWidgets.QVBoxLayout()
        titleLO = QtWidgets.QHBoxLayout()
        titleLO.addWidget(QtWidgets.QLabel('Project Title:'))
        titleLO.addWidget(titleBox)
        totalLayout.addLayout(titleLO)
        fileLO = QtWidgets.QHBoxLayout()
        fileLO.addWidget(QtWidgets.QLabel('Input Data File:'))
        fileLO.addWidget(fileLine)
        fileLO.addWidget(fileButton)
        totalLayout.addLayout(fileLO)
        sheetLO = QtWidgets.QHBoxLayout()
        sheetLO.addWidget(QtWidgets.QLabel('Sheet Name:'))
        sheetLO.addWidget(sheetLine)
        totalLayout.addLayout(sheetLO)
        intervalLO = QtWidgets.QHBoxLayout()
        intervalLO.addWidget(QtWidgets.QLabel('Time Interval Size:'))
        intervalLO.addWidget(intervalLine)
        totalLayout.addLayout(intervalLO)
        #totalLayout.addWidget(ctlBox)
        threshLO = QtWidgets.QHBoxLayout()
        threshLO.addWidget(QtWidgets.QLabel('Correlation Threshold:'))
        threshLO.addWidget(corrThreshLine)
        totalLayout.addLayout(threshLO)
        totalLayout.addWidget(nodeColorRainbow)
        totalLayout.addWidget(nodeColorRed)
        totalLayout.addWidget(runButton)
        totalLayout.addWidget(batchButton)
        self.setLayout(totalLayout)
        self.setWindowTitle('DyNA')

        fileButton.clicked.connect(lambda: self.getFile(fileLine))
        ctlFileButton.clicked.connect(lambda: self.getFile(ctlFileLine))
        runButton.clicked.connect(lambda: self.run(fileLine.text(),sheetLine.text(),int(intervalLine.text()),
                                                   #ctlBox.isChecked(),ctlFileLine.text(),ctlSheetLine.text(),
                                                   float(corrThreshLine.text()),titleBox.text(),nodeColorRainbow.isChecked()))
        batchButton.clicked.connect(lambda: self.runBatch(fileLine.text(),sheetLine.text(),int(intervalLine.text()),
                                                          titleBox.text(),nodeColorRainbow.isChecked()))#run for-loop of run's function, with corrthreshes 0.7 -> 0.95 in 0.05 intervals

    def getFile(self, fileLineEdit):
        fileBox = QtWidgets.QFileDialog(self)
        inFile = QtCore.QFileInfo(fileBox.getOpenFileName(None, filter='*.xls* *.csv')[0])
        filepath = inFile.absoluteFilePath()
        if any([filepath.endswith('.xls'),
                filepath.endswith('.xlsx'),
                filepath.endswith('.csv')]):
            fileLineEdit.setText(filepath)

    def readFile(self,path,sheet):
        if len(path) < 1:
            QtWidgets.QMessageBox.warning(self, 'Error: No Input File',
                                          'Please select an input file and try again.')
            return 0
        data = pandas.DataFrame()
        if(path.endswith('.xls') or path.endswith('.xlsx')):
            data = pandas.read_excel(path,sheet_name=sheet,header=0)
        if(path.endswith('.csv')):
            df = pandas.read_csv(path,engine='python',header=0,iterator=True,chunksize=15000)
            data = pandas.DataFrame(pandas.concat(df,ignore_index=True))
        data = data.dropna(axis='index',how='all')
        return data

    def timePointGraphs(self,dynadata,days,kt,label,corrThresh,outputTitle,colorfulChecked):
        k = len(days)
        # Create color map, if needed
        colorList = [matplotlib.colormaps['Pastel2'](float(c / len(label))) for c in range(len(label))]
        # The Big Loop
        dynaTitles = []
        resultColumns = []
        networkComplex = []
        positiveEdges = []
        negativeEdges = []
        for i in range(k - kt + 1):
            dynaMatrixSubsets = []
            good = []
            dynaTitle = days[i] + ' - ' + days[i + kt - 1]
            dynaTitles.append(dynaTitle)
            for j in range(kt):
                dynaMatrixSubsets.append(dynadata[i + j])
            dynaMatrixRaw = pandas.concat(dynaMatrixSubsets, ignore_index=True, sort=False).T
            dynaMatrixCorr = numpy.corrcoef(dynaMatrixRaw)
            dynaMatrix = dynaMatrixCorr - numpy.eye(dynaMatrixCorr.shape[0])
            adjMatrix = numpy.zeros(shape=(dynaMatrix.shape[0], dynaMatrix.shape[0]))
            coordsArray = numpy.argwhere(abs(dynaMatrix) >= corrThresh)
            for e in range(len(coordsArray)):
                adjMatrix[coordsArray[e, 0], coordsArray[e, 1]] = 1
            # Begin preprocessing for graph
            label2 = []
            labelDict = {}
            '''
            if ctlBool and len(rawControl.index) > 0:
                for r in range(len(label)):
                    h = []
                    for t in range(kt):
                        tempdata = dynadata[i + t]
                        tempcontrol = rawControl.iloc[:, r + 2]
                        ttestStat, p, degFreedom = scipy.stats.ttest_ind(tempcontrol, tempdata.iloc[:, r],
                                                                         alternative='two-sided')
                        if p < 0.05:
                            h.append(1)
                        else:
                            h.append(0)
                    if sum(h) > 0:
                        good.append(r)
                    adjMatrix = adjMatrix[numpy.ix_(good, good)]
                    label2 = [label[g] for g in good]  # it resets label in the original, that /can't/ be right
            else:
            '''
            good = range(len(label))
            label2 = label
            for l in range(len(label2)):
                labelDict[l] = label2[l]
            if len(good) > 0:
                ee = len(label2)
                if ee > 1:
                    numberEdge = sum(sum(adjMatrix)) / 2
                    networkComplex.append(numberEdge * 2 / (ee * (ee - 1)) * ee)
                    goodCol = pandas.Series(data=sum(adjMatrix), index=label2, name=(days[i] + '-' + days[i+1]))
                    resultColumns.append(goodCol)
                else:
                    networkComplex.append(0)
                dynaMatrix = dynaMatrix[numpy.ix_(good, good)]
                coordsArray2 = numpy.argwhere(dynaMatrix <= (-1 * corrThresh))
                edgeColor = []
                if len(coordsArray2) > 0:
                    for k2 in range(len(coordsArray2)):
                        edgeColor.append([coordsArray2[k2,0],coordsArray2[k2,1]])  # see below for negative connection handling
                    negativeEdges.append(len(coordsArray2))
                    positiveEdges.append(sum(sum(adjMatrix)) / 2 - len(coordsArray2))
                else:
                    negativeEdges.append(0)
                    positiveEdges.append(sum(sum(adjMatrix)) / 2)
                G = nx.from_numpy_array(adjMatrix, parallel_edges=False)
                pos = nx.circular_layout(G)
                node_colors = []
                if colorfulChecked:
                    node_colors = [colorList[n] if len(G.edges(n)) > 0 else "white" for n in G.nodes()]
                else:
                    node_colors = ["red" if len(G.edges(n)) > 0 else "lemonchiffon" for n in G.nodes()]
                node_opts = {"node_size": 750, "node_color": node_colors, "edgecolors": "k", "linewidths": 1.0}
                fig, ax = plt.subplots()
                nx.draw_networkx_nodes(G, pos, **node_opts)
                nx.draw_networkx_labels(G, pos, labelDict, font_size=12,font_weight='bold')
                nx.draw_networkx_edges(G, pos, width=2, arrows=True, arrowstyle='<->')
                if len(coordsArray2) > 0:
                    nx.draw_networkx_edges(G, pos, edgelist=edgeColor, edge_color="r", width=2)
                plt.suptitle(outputTitle + ' ' + dynaTitle+ ' ' + str(corrThresh))
                fig.set_layout_engine('constrained')
                plt.savefig(outputTitle + ' ' + dynaTitle + ' ' + str(corrThresh) + '.tiff')
                plt.close()
            else:
                networkComplex.append(0)
        posNegConnections = pandas.DataFrame(data=[positiveEdges, negativeEdges], columns=dynaTitles,
                                             index=['Positive', 'Negative'])
        posNegConnections.loc['Total'] = posNegConnections.sum(axis='index')
        posNegConnections.loc[:, 'Total'] = posNegConnections.sum(axis='columns')
        results = pandas.concat(resultColumns, axis=1, ignore_index=False, join='outer')
        results.loc['Total'] = results.sum(axis='index') / 2
        results['Total'] = results.sum(axis='columns')
        return posNegConnections, results, dynaTitles, networkComplex

    def run(self, file, sheet, kt, corrThresh, outputTitle,colorfulChecked): #ctlBool, ctlFile, ctlSheet,
        #kt: interval size
        #k: number of time points
        #days: list of time points
        #label: list of parameters being correlated
        rawData = self.readFile(file,sheet)
        if len(rawData) < 2:
            return 0
        #rawControl = self.readFile(file,sheet)
        days = sorted(list(set(rawData.iloc[:,1])))
        k = len(days)
        if kt < 1 or kt > k:
            ktErr = QtWidgets.QMessageBox.warning(self,'Error: Invalid Time Interval Entered',
                                                  'Please select a time interval between 1 and the total number of time points in your data.')
            return 0
        label = list(rawData.columns)[2:]
        dataCols = list(rawData.columns)
        timeCol = dataCols[1]
        dynadata = []
        newdata = rawData.sort_values(by=timeCol,ascending=True).reset_index(drop=True)
        newdata = newdata.dropna(subset=[timeCol])
        #Report error for blank cells?
        for d in range(len(days)):
            index = list(newdata[newdata[timeCol]==days[d]].index)
            dynadata.append(newdata.iloc[index,2:])
        posNegConnections, results, dynaTitles, networkComplex = self.timePointGraphs(dynadata,days,kt,label,corrThresh,
                                                                                      outputTitle,colorfulChecked)
        fig, ax = plt.subplots()
        plt.plot(dynaTitles,networkComplex,'o-k')
        ax.xaxis.set_tick_params(rotation=45)
        plt.suptitle(outputTitle + ' Network Complexity')
        fig.set_layout_engine('constrained')
        plt.savefig(outputTitle + ' Network Complexity.tiff')
        plt.close()
        writer = pandas.ExcelWriter(outputTitle+' DyNA.xlsx',engine='xlsxwriter')
        results.to_excel(writer,'# Connections',engine='xlsxwriter',index=True)
        posNegConnections.to_excel(writer,'Pos v Neg Connections',engine='xlsxwriter',index=True)
        writer.close()
        successMessage = QtWidgets.QMessageBox.information(self, 'Success!',
                                              'Your DyNA has finished successfully!')
        return 0

    def runBatch(self,file, sheet, kt, outputTitle,colorfulChecked):
        # kt: interval size
        # k: number of time points
        # days: list of time points
        # label: list of parameters being correlated
        rawData = self.readFile(file, sheet)
        if not len(rawData) >= 2:
            return 0
        # rawControl = self.readFile(file,sheet)
        days = sorted(list(set(rawData.iloc[:, 1])))
        k = len(days)
        if kt < 1 or kt > k:
            ktErr = QtWidgets.QMessageBox.warning(self, 'Error: Invalid Time Interval Entered',
                                                  'Please select a time interval between 1 and the total number of time points in your data.')
            return 0
        label = list(rawData.columns)[2:]
        # check to see if columns overlap between data and control?
        dataCols = list(rawData.columns)
        timeCol = dataCols[1]
        dynadata = []
        newdata = rawData.sort_values(by=timeCol, ascending=True).reset_index(drop=True)
        newdata = newdata.dropna(subset=[timeCol])
        # Report error for blank cells?
        for d in range(len(days)):
            index = list(newdata[newdata[timeCol] == days[d]].index)
            dynadata.append(newdata.iloc[index, 2:])
        corrThreshList = [0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
        netCompSeries = []
        allResults = []
        allPosNeg = []
        allDyNATitles = []
        for corrThresh in corrThreshList:
            posNegConnections, results, dynaTitles, networkComplex = self.timePointGraphs(dynadata, days, kt, label,
                                                                                          corrThresh,
                                                                                          outputTitle, colorfulChecked)
            netCompSeries.append(pandas.Series(data=networkComplex,index=dynaTitles,name=str(corrThresh)))
            results.insert(0,'Threshold',corrThresh)
            posNegConnections.insert(0,'Threshold',corrThresh)
            allResults.append(results)
            allPosNeg.append(posNegConnections)
            allDyNATitles = dynaTitles
        netCompDF = pandas.concat(netCompSeries,axis=1)
        allResultsDF = pandas.concat(allResults)
        allPosNegDF = pandas.concat(allPosNeg)
        fig, ax = plt.subplots()
        plt.plot(allDyNATitles, netCompDF, marker = 'o', linestyle='solid')
        ax.xaxis.set_tick_params(rotation=45)
        ax.legend(corrThreshList,loc='center left', bbox_to_anchor=(1.02, 0.5))
        plt.suptitle(outputTitle + ' Network Complexity')
        fig.set_layout_engine('constrained')
        plt.savefig(outputTitle + ' Network Complexity.tiff')
        plt.close()
        writer = pandas.ExcelWriter(outputTitle + ' DyNA.xlsx', engine='xlsxwriter')
        allResultsDF.to_excel(writer, '# Connections', engine='xlsxwriter', index=True)
        allPosNegDF.to_excel(writer, 'Pos v Neg Connections', engine='xlsxwriter', index=True)
        writer.close()
        successMessage = QtWidgets.QMessageBox.information(self, 'Success!',
                                                           'Your DyNA has finished successfully!')
        return 0


form = Form()
form.show()
app.exec_()