# -*- coding: utf-8 -*-
'''
DyNA: Dynamic Network Analysis
Translated into Python by Fayten El-Dehaibi
Python file created 13 Dec 2024
'''

import sys
import os
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
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
        totalLayout.addWidget(runButton)
        self.setLayout(totalLayout)
        self.setWindowTitle('DyNA')

        fileButton.clicked.connect(lambda: self.getFile(fileLine))
        ctlFileButton.clicked.connect(lambda: self.getFile(ctlFileLine))
        runButton.clicked.connect(lambda: self.run(fileLine.text(),sheetLine.text(),int(intervalLine.text()),
                                                   ctlBox.isChecked(),ctlFileLine.text(),ctlSheetLine.text(),
                                                   float(corrThreshLine.text()),titleBox.text()))

    def getFile(self, fileLineEdit):
        fileBox = QtWidgets.QFileDialog(self)
        inFile = QtCore.QFileInfo(fileBox.getOpenFileName(None, filter='*.xls* *.csv')[0])
        filepath = inFile.absoluteFilePath()
        if any([filepath.endswith('.xls'),
                filepath.endswith('.xlsx'),
                filepath.endswith('.csv')]):
            fileLineEdit.setText(filepath)

    def readFile(self,path,sheet):
        data = pandas.DataFrame()
        if(path.endswith('.xls') or path.endswith('.xlsx')):
            data = pandas.read_excel(path,sheet_name=sheet,header=0)
        if(path.endswith('.csv')):
            df = pandas.read_csv(path,engine='python',header=0,iterator=True,chunksize=15000)
            data = pandas.DataFrame(pandas.concat(df,ignore_index=True))
        return data

    def run(self, file, sheet, kt, ctlBool, ctlFile, ctlSheet, corrThresh, outputTitle):
        #kt: interval size
        #k: number of time points
        #days: list of time points
        #label: list of parameters being correlated
        rawData = self.readFile(file,sheet)
        rawControl = self.readFile(file,sheet)
        days = sorted(list(set(rawData.iloc[:,1])))
        k = len(days)
        if kt < 1 or kt > k:
            ktErr = QtWidgets.QMessageBox.warning(self,'Error: Invalid Time Interval Entered',
                                                  'Please select a time interval between 1 and the total number of time points in your data.')
            return 0
        label = list(rawData.columns)[2:]
        #check to see if columns overlap between data and control?
        dataCols = list(rawData.columns)
        timeCol = dataCols[1]
        dynadata = []
        newdata = rawData.sort_values(by=timeCol,ascending=True).reset_index(drop=True)
        newdata = newdata.dropna(subset=[timeCol])
        #Report error for blank cells?
        for d in range(len(days)):
            index = list(newdata[newdata[timeCol]==days[d]].index)
            dynadata.append(newdata.iloc[index,2:])
        #The Big Loop
        dynaTitles = []
        pages = []
        networkComplex = []
        for i in range(k-kt+1):
            dynaMatrixSubsets = []
            good = []
            dynaTitle = days[i] + ' - ' + days[i+kt-1]
            dynaTitles.append(dynaTitle)
            for j in range(kt):
                dynaMatrixSubsets.append(dynadata[i+j])
            dynaMatrixRaw = pandas.concat(dynaMatrixSubsets, ignore_index=True, sort=False).T#do I need to transpose this so that params are index labels, instead of time values?
            dynaMatrixCorr = numpy.corrcoef(dynaMatrixRaw)
            dynaMatrix = dynaMatrixCorr - numpy.eye(dynaMatrixCorr.shape[0])
            adjMatrix = numpy.zeros(shape=(dynaMatrix.shape[0],dynaMatrix.shape[0]))
            coordsArray = numpy.argwhere(abs(dynaMatrix) >= corrThresh)
            for e in range(len(coordsArray)):
                adjMatrix[coordsArray[e,0],coordsArray[e,1]] = 1
            #Begin preprocessing for graph
            label2 = []
            labelDict = {}
            if ctlBool and len(rawControl.index) > 0:
                for r in range(len(label)):
                    h = []
                    for t in range(kt):
                        tempdata = dynadata[i+t]
                        tempcontrol = rawControl.iloc[:,r+2]
                        ttestStat, p, degFreedom = scipy.stats.ttest_ind(tempcontrol,tempdata.iloc[:,r],alternative='two-sided')
                        if p < 0.05:
                            h.append(1)
                        else:
                            h.append(0)
                    if sum(h) > 0:
                        good.append(r)
                    adjMatrix = adjMatrix[numpy.ix_(good,good)]
                    label2 = [label[g] for g in good] #it resets label in the original, that /can't/ be right
            else:
                good = range(len(label))
                label2 = label
            for l in range(len(label2)):
                labelDict[l] = label2[l]
            if len(good) > 0:
                ee = len(label2)
                if ee > 1:
                    numberEdge = sum(sum(adjMatrix))/2
                    networkComplex.append(numberEdge * 2 / (ee*(ee-1))*ee)
                else:
                    networkComplex.append(0)
                dynaMatrix = dynaMatrix[numpy.ix_(good,good)]
                coordsArray2 = numpy.argwhere(dynaMatrix <= (-1*corrThresh)) #change function to numpy.nonzero ?
                edgeColor = []
                for k2 in range(len(coordsArray2)):
                    edgeColor.append([label2(coordsArray2[k2][0]),label2(coordsArray2[k2][1])])#see below for negative connection handling
                G = nx.from_numpy_array(adjMatrix,parallel_edges=False)
                pos = nx.circular_layout(G)
                node_opts = {"node_size": 500, "node_color": "lemonchiffon", "edgecolors": "k", "linewidths": 1.0}
                nx.draw_networkx_nodes(G, pos, **node_opts)
                nx.draw_networkx_labels(G, pos, labelDict, font_size=6)
                nx.draw_networkx_edges(G,pos,width=2)
                if len(coordsArray2) > 0:
                    nx.draw_networkx_edges(G, pos, edgelist=edgeColor, edge_color="r", width=2)
                plt.suptitle(dynaTitle)
                plt.savefig(outputTitle+' '+dynaTitle+'.tiff')
                print()
                #write node info into file
                #append file to pages
            else:
                networkComplex.append(0)



form = Form()
form.show()
app.exec_()