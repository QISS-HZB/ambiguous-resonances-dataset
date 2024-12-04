#! /usr/bin/env python3
"""
This file contains the GUI application for the dataset of the paper "Ambiguous Resonances in Multipulse Quantum Sensing with Nitrogen Vacancy Centers in Diamonds" by L. Tsunaki et al, available at https://arxiv.org/abs/2407.09411 .
The hdf5 file for the dataset is provided at https://figshare.com/articles/dataset/Dataset_for_Ambiguous_Resonances_in_Multipulse_Quantum_Sensing_with_NVs/26245895 .

The script instantiates and runs the GUI window, and sets up the analysis parameters after reading the HDF5 dataset file.
The entire application for now is in a gigantic class with a bunch of repeated methods which initialise and set up all the necessary widgets and layouts.
The function `load_data()` is the entry point which provides the values of all the parameters upon which the widgets and layouts are created (see `__init__` for the implementaion.).
Visualisation is handled by matplotlib through the respective update_plot functions, which read the selected parameters and control the plot drawn for each tab (N15 and C13).

Version: 1.3
Date: 31-07-2024
License: GPL-3.0
"""

import os
import tables as tb
import argparse
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Tries to import either PySide6 or PyQt6 depending on the user's environment
try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QLabel,
        QComboBox,
        QPushButton,
        QWidget,
        QVBoxLayout,
        QCheckBox,
        QHBoxLayout,
        QFileDialog,
        QListWidget,
        QAbstractItemView,
        QFormLayout,
        QMessageBox,
        QTabWidget,
        QRadioButton,
        QButtonGroup,
        QListWidgetItem,
    )
    from PySide6.QtCore import Qt
except ImportError:
    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QLabel,
        QComboBox,
        QPushButton,
        QWidget,
        QVBoxLayout,
        QCheckBox,
        QHBoxLayout,
        QFileDialog,
        QListWidget,
        QAbstractItemView,
        QFormLayout,
        QMessageBox,
        QRadioButton,
        QButtonGroup,
        QListWidgetItem,
    )
    from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure

matplotlib.use("QtAgg")

plt.rcParams.update({"font.size": 3})
colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--dataset", default="./dataset.h5")
args = parser.parse_args()


class InteractivePlotApp(QMainWindow):
    """
    Class for the application window.

    Class Methods
    -------------
        set_tab_15N(self) : Sets the layout for the 15N tab, with its widgets and buttons.
        set_tab_13C(self) : Sets the tab for 13C, with its widgets and buttons.
        load_data(self) : Loads the data from the dataset file based on the parametes selected by the user.
        resizeEvent(self, event) : Updates the GUI based on the tab selected by the user.
        select_all_gyro_N(self) : Selects all gyromagnetic ratios in the list to compare with ambiguous resonances from 15N.
        clear_gyro_N(self) : Clears the selection of gyromagnetic ratios in the list to compare with ambiguous resonances from 15N.
        select_all_items_C(self) : Selects all simulations for the 13C families to plot.
        clear_selection_C(self) : Clears the selection of simulations for the 13C families to plot.
        select_all_gyro_C(self) : Selects all gyromagnetic ratios in the list to compare with ambiguous resonances from 13C.
        clear_gyro_C(self) : Clears the selection of gyromagnetic ratios in the list to compare with ambiguous resonances from 13C.
        set_right_layout(self) : Intializes the plot on the right side of the grid with an empty plot.
        select_file_N(self) : Select the experimental data file for 15N.
        select_file_C(self) : Select the experimental data file for 13C.
        update_plot_N(self) : Update the plot with the selected parameters for 15N.
        update_plot_C(self) : Update the plot with the selected parameters for 13C.
    """

    def __init__(self):
        """
        Sets up the GUI window.

        The structure is as follows:

        The `main_layout` is horizontal with the controls on the left and graphs on the right. The `init` function creates the main and the left and the right layouts via the respective functions.
        The control pane consists of a tab each for N-15 and C-13, which are again created in their respective "set functions". These functions perform the bulk of the work.
        The graph view is provided by matplotlib and is set up in `set_right_layout`

        The parameter `plot_ready` is used to update a ready plot upon window resize through the function `resizeEvent`.
        """
        super().__init__()
        self.load_data()

        self.plot_ready = False

        self.main_layout = QHBoxLayout()
        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle("Dataset for Ambiguous Resonances in Multipulse Quantum Sensing with NVs")
        self.showMaximized()

        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()

        self.tab_15N = QWidget()
        self.tab_15N_layout = QVBoxLayout()
        self.tab_15N.setLayout(self.tab_15N_layout)

        self.tab_13C = QWidget()
        self.tab_13C_layout = QVBoxLayout(self.tab_13C)

        self.set_tab_15N()
        self.set_tab_13C()

        self.tab_widget.addTab(self.tab_15N, "¹⁵N")
        self.tab_widget.addTab(self.tab_13C, "¹³C")

        self.left_layout.addWidget(self.tab_widget)
        self.set_right_layout()

        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addLayout(self.right_layout)

    def set_tab_15N(self):
        """
        Sets the layout for the 15N tab, with its widgets and buttons.
        """

        self.ms_label_N = QLabel("m<sub>s</sub> state:")
        self.ms_widget_N = QComboBox()
        self.ms_widget_N.addItems(["-1", "1"])
        self.ms_label_N.setToolTip(
            "Electronic spin state. For magnetic fields near the level anti-crossing (53.2 mT), the state ms=-1 is "
            "close to ms=0 and the system might not present well defined spin manipulations."
        )

        # XY8-M order
        self.M_label_N = QLabel("M:")
        self.M_widget_N = QComboBox()
        self.M_widget_N.addItems([str(val) for val in self.M_n])
        self.M_label_N.setToolTip(
            "Order of the XY8-M sequence. For high order, the exact duration of the pi pulses becomes important "
            "factor. In these simulations we used w1 = 40 MHz, in order to avoid spurious resonances from long pulses."
        )

        # External magnetic field intensity
        self.B0_label_N = QLabel("B\N{SUBSCRIPT ZERO} (mT):")
        self.B0_widget_N = QComboBox()
        self.B0_widget_N.setMaxVisibleItems(20)
        self.B0_widget_N.addItems([str(val) for val in self.B0_n])
        self.B0_label_N.setToolTip(
            "Intensity of the external magnetic field. At low magnetic fields, both electronic spin states are nearly "
            "degenerate and the system presents a complex S=1 dynamics, which may lead to not well defined pulses."
        )

        # Misalignment angle
        self.theta_label_N = QLabel("θ (°):")
        self.theta_widget_N = QComboBox()
        self.theta_widget_N.addItems([str(val) for val in self.theta])
        self.theta_label_N.setToolTip(
            "Angle between the external magnetic field and the quantization axis of the electron spin. At high angles "
            "and fields, the nuclear spin is not good quantum number and the Hamiltonian might not represent "
            "faithfully the system."
        )

        left_form_layout = QFormLayout()
        left_form_layout.addRow(self.ms_label_N, self.ms_widget_N)
        left_form_layout.addRow(self.M_label_N, self.M_widget_N)
        left_form_layout.addRow(self.B0_label_N, self.B0_widget_N)
        left_form_layout.addRow(self.theta_label_N, self.theta_widget_N)

        self.tab_15N_layout.addLayout(left_form_layout)

        # Optional experimental data file to compare with
        self.expt_file_label_N = QLabel("No file selected")

        self.expt_file_btn_N = QPushButton("Select file")
        self.expt_file_btn_N.clicked.connect(self.select_file_N)

        expt_HLay = QHBoxLayout()
        self.expt_label_N = QLabel("Compare with experimental Data")
        self.expt_chkbox_N = QCheckBox()
        expt_HLay.addWidget(self.expt_label_N)
        expt_HLay.addWidget(self.expt_chkbox_N)

        self.expt_label_N.setToolTip(
            "Experimental data must be in a file with two columns: first column is the pulse separation tau or frequency "
            "the second column is the transition probability."
        )
        self.expt_filename_N = ""  # to handle plotting when no file is selected

        self.tab_15N_layout.addWidget(self.expt_file_label_N)
        self.tab_15N_layout.addWidget(self.expt_file_btn_N)

        self.tab_15N_layout.addLayout(expt_HLay)

        self.gyromagnetic_label = QLabel("Compare peaks with:")
        self.gyromagnetic_widget_N = QListWidget()
        for key in self.gyromagnetic_ratios.keys():
            item = QListWidgetItem()
            item.setData(Qt.UserRole, key)
            label = QLabel(key)
            label.setTextFormat(Qt.TextFormat.RichText)
            self.gyromagnetic_widget_N.addItem(item)
            self.gyromagnetic_widget_N.setItemWidget(item, label)

        self.gyromagnetic_widget_N.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.gyromagnetic_label.setToolTip("The corresponding tau is 1/(2*γ*B<sub>0</sub>).")

        self.tab_15N_layout.addWidget(self.gyromagnetic_label)
        self.tab_15N_layout.addWidget(self.gyromagnetic_widget_N)

        self.select_all_button_N = QPushButton("Select all")
        self.clear_button_N = QPushButton("Clear selection")

        self.select_all_button_N.clicked.connect(self.select_all_gyro_N)
        self.clear_button_N.clicked.connect(self.clear_gyro_N)

        gyromagnetic_btn_lay = QFormLayout()
        gyromagnetic_btn_lay.addRow(self.select_all_button_N, self.clear_button_N)
        self.tab_15N_layout.addLayout(gyromagnetic_btn_lay)

        self.plot_x_layout_N = QVBoxLayout()
        self.plot_x_btn_layout_N = QHBoxLayout()

        self.plot_x_layout_N.addWidget(QLabel("Plot against (x-axis)"))

        self.radio1_N = QRadioButton("τ")
        self.radio2_N = QRadioButton("f")

        self.radio1_N.setChecked(True)

        self.plot_x_btngrp_N = QButtonGroup()
        self.plot_x_btngrp_N.addButton(self.radio1_N)
        self.plot_x_btngrp_N.addButton(self.radio2_N)

        self.plot_x_btn_layout_N.addWidget(self.radio1_N)
        self.plot_x_btn_layout_N.addWidget(self.radio2_N)

        self.plot_x_layout_N.addLayout(self.plot_x_btn_layout_N)
        self.tab_15N_layout.addLayout(self.plot_x_layout_N)

        self.unit_layout_N = QVBoxLayout()
        self.unit_btn_layout_N = QHBoxLayout()

        self.unit_layout_N.addWidget(QLabel("Units (τ/f):"))

        self.unit_btn1_N = QRadioButton("ns/GHz")
        self.unit_btn2_N = QRadioButton("μs/MHz")
        self.unit_btn3_N = QRadioButton("ms/kHz")
        self.unit_btn4_N = QRadioButton("s/Hz")

        self.unit_btn2_N.setChecked(True)

        self.unit_btngrp_N = QButtonGroup()
        self.unit_btngrp_N.addButton(self.unit_btn1_N, id=0)
        self.unit_btngrp_N.addButton(self.unit_btn2_N, id=1)
        self.unit_btngrp_N.addButton(self.unit_btn3_N, id=2)
        self.unit_btngrp_N.addButton(self.unit_btn4_N, id=3)

        self.unit_btn_layout_N.addWidget(self.unit_btn1_N)
        self.unit_btn_layout_N.addWidget(self.unit_btn2_N)
        self.unit_btn_layout_N.addWidget(self.unit_btn3_N)
        self.unit_btn_layout_N.addWidget(self.unit_btn4_N)

        self.unit_layout_N.addLayout(self.unit_btn_layout_N)
        self.tab_15N_layout.addLayout(self.unit_layout_N)

        self.update_button_N = QPushButton("Update plot")
        self.update_button_N.clicked.connect(self.update_plot_N)
        self.tab_15N_layout.addWidget(self.update_button_N)

    def set_tab_13C(self):
        """
        Sets the tab for 13C, with its widgets and buttons.
        """
        self.ms_label_C = QLabel("m<sub>s</sub> state:")
        self.ms_widget_C = QComboBox()
        self.ms_widget_C.addItems(["-1", "1"])
        self.ms_label_C.setToolTip(
            "Electronic spin state. For magnetic fields near the level anti-crossing (53.2 mT), the state ms=-1 is "
            "close to ms=0 and the system might not present well defined spin manipulations."
        )

        # XY8-M order
        self.M_label_C = QLabel("M:")
        self.M_widget_C = QComboBox()
        self.M_widget_C.addItems([str(val) for val in self.M_C])
        self.M_label_C.setToolTip(
            "Order of the XY8-M sequence. For high order, the exact duration of the pi pulses becomes important "
            "factor. In these simulations we used w1 = 40 MHz, in order to avoid spurious resonances from long pulses."
        )

        # External magnetic field intensity
        self.B0_label_C = QLabel("B\N{SUBSCRIPT ZERO} (mT):")
        self.B0_widget_C = QComboBox()
        self.B0_widget_C.setMaxVisibleItems(20)
        self.B0_widget_C.addItems([str(val) for val in self.B0_C])
        self.B0_label_C.setToolTip(
            "Intensity of the external magnetic field. At low magnetic fields, both electronic spin states are nearly "
            "degenerate and the system presents a complex S=1 dynamics, which may lead to not well defined pulses."
        )

        left_form_layout = QFormLayout()
        left_form_layout.addRow(self.ms_label_C, self.ms_widget_C)
        left_form_layout.addRow(self.M_label_C, self.M_widget_C)
        left_form_layout.addRow(self.B0_label_C, self.B0_widget_C)

        self.tab_13C_layout.addLayout(left_form_layout)

        # Optional experimental data file to compare with
        self.expt_file_label_C = QLabel("No file selected")

        self.expt_file_btn_C = QPushButton("Select file")
        self.expt_file_btn_C.clicked.connect(self.select_file_C)

        expt_HLay = QHBoxLayout()
        self.expt_label_C = QLabel("Compare with experimental Data")
        self.expt_chkbox_C = QCheckBox()
        expt_HLay.addWidget(self.expt_label_C)
        expt_HLay.addWidget(self.expt_chkbox_C)

        self.expt_label_C.setToolTip(
            "Experimental data must be in a file with two columns: first column is the pulse separation tau or frequency and "
            "the second column is the transition probability."
        )
        self.expt_filename_C = ""  # to handle plotting when no file is selected

        self.tab_13C_layout.addWidget(self.expt_file_label_C)
        self.tab_13C_layout.addWidget(self.expt_file_btn_C)

        self.tab_13C_layout.addLayout(expt_HLay)

        self.families_label = QLabel("¹³C Families:")
        self.families_widget = QListWidget()
        self.families_widget.addItems([fam_value for fam_value in self.fam])
        self.families_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.families_label.setToolTip("The corresponding tau is 1/(2*γ*B<sub>0</sub>).")

        self.tab_13C_layout.addWidget(self.families_label)
        self.tab_13C_layout.addWidget(self.families_widget)

        self.select_all_button_C = QPushButton("Select all")
        self.clear_button_C = QPushButton("Clear selection")

        self.select_all_button_C.clicked.connect(self.select_all_items_C)
        self.clear_button_C.clicked.connect(self.clear_selection_C)

        fam_btn_layout = QFormLayout()
        fam_btn_layout.addRow(self.select_all_button_C, self.clear_button_C)
        self.tab_13C_layout.addLayout(fam_btn_layout)

        self.gyromagnetic_label_C = QLabel("Compare peaks with:")
        self.gyromagnetic_widget_C = QListWidget()

        for key in self.gyromagnetic_ratios.keys():
            item = QListWidgetItem()
            item.setData(Qt.UserRole, key)
            label = QLabel(key)
            label.setTextFormat(Qt.TextFormat.RichText)
            self.gyromagnetic_widget_C.addItem(item)
            self.gyromagnetic_widget_C.setItemWidget(item, label)

        self.gyromagnetic_widget_C.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.gyromagnetic_label_C.setToolTip("The corresponding tau is 1/(2*γ*B<sub>0</sub>).")

        self.tab_13C_layout.addWidget(self.gyromagnetic_label_C)
        self.tab_13C_layout.addWidget(self.gyromagnetic_widget_C)

        self.select_all_btn_gyro_C = QPushButton("Select all")
        self.clear_btn_gyro_C = QPushButton("Clear selection")

        self.select_all_btn_gyro_C.clicked.connect(self.select_all_gyro_C)
        self.clear_btn_gyro_C.clicked.connect(self.clear_gyro_C)

        gyro_btn_layout = QFormLayout()
        gyro_btn_layout.addRow(self.select_all_btn_gyro_C, self.clear_btn_gyro_C)
        self.tab_13C_layout.addLayout(gyro_btn_layout)

        self.plot_x_layout_C = QVBoxLayout()
        self.plot_x_btn_layout_C = QHBoxLayout()

        self.plot_x_layout_C.addWidget(QLabel("Plot against (x-axis)"))

        self.radio1_C = QRadioButton("τ")
        self.radio2_C = QRadioButton("f")

        self.radio1_C.setChecked(True)

        self.plot_x_btngrp_C = QButtonGroup()
        self.plot_x_btngrp_C.addButton(self.radio1_C)
        self.plot_x_btngrp_C.addButton(self.radio2_C)

        self.plot_x_btn_layout_C.addWidget(self.radio1_C)
        self.plot_x_btn_layout_C.addWidget(self.radio2_C)

        self.plot_x_layout_C.addLayout(self.plot_x_btn_layout_C)
        self.tab_13C_layout.addLayout(self.plot_x_layout_C)

        self.unit_layout_C = QVBoxLayout()
        self.unit_btn_layout_C = QHBoxLayout()

        self.unit_layout_C.addWidget(QLabel("Units (τ/f):"))

        self.unit_btn1_C = QRadioButton("ns/GHz")
        self.unit_btn2_C = QRadioButton("μs/MHz")
        self.unit_btn3_C = QRadioButton("ms/kHz")
        self.unit_btn4_C = QRadioButton("s/Hz")

        self.unit_btn2_C.setChecked(True)

        self.unit_btngrp_C = QButtonGroup()
        self.unit_btngrp_C.addButton(self.unit_btn1_C, id=0)
        self.unit_btngrp_C.addButton(self.unit_btn2_C, id=1)
        self.unit_btngrp_C.addButton(self.unit_btn3_C, id=2)
        self.unit_btngrp_C.addButton(self.unit_btn4_C, id=3)

        self.unit_btn_layout_C.addWidget(self.unit_btn1_C)
        self.unit_btn_layout_C.addWidget(self.unit_btn2_C)
        self.unit_btn_layout_C.addWidget(self.unit_btn3_C)
        self.unit_btn_layout_C.addWidget(self.unit_btn4_C)

        self.unit_layout_C.addLayout(self.unit_btn_layout_C)
        self.tab_13C_layout.addLayout(self.unit_layout_C)

        # update button
        self.update_button_C = QPushButton("Update plot")
        self.update_button_C.clicked.connect(self.update_plot_C)
        self.tab_13C_layout.addWidget(self.update_button_C)

    def load_data(self):
        """
        Loads and processes the data from the hdf5 file.
        """
        self.dataset_file = tb.open_file(args.dataset, "r")

        self.N15_table = self.dataset_file.root.n15_group.n15_table
        self.theta = np.unique(self.N15_table.col("field_angle"))
        self.B0_n = np.unique(self.N15_table.col("field"))
        self.M_n = np.unique(self.N15_table.col("order"))

        self.C13_table = self.dataset_file.root.c13_group.c13_table
        self.B0_C = np.unique(self.C13_table.col("field"))
        self.M_C = np.unique(self.C13_table.col("order"))

        # microseconds and megahertz
        self.tau = np.linspace(0.05, 3, 1000)
        self.freq = 1 / 2 / self.tau

        self.gyro_table = self.dataset_file.root.val_group.gyro_table
        self.cfam_table = self.dataset_file.root.val_group.cfam_table

        self.gyromagnetic_ratios_raw = {
            k.decode("utf-8"): v
            for k, v in zip(self.gyro_table.col("substance"), self.gyro_table.col("value"))
        }

        # MHz/Tesla
        self.gyromagnetic_ratios = {}
        for k, v in self.gyromagnetic_ratios_raw.items():
            temp_part = k.split("-")
            self.gyromagnetic_ratios[f"<sup>{temp_part[1]}</sup>{temp_part[0]}"] = v

        self.fam = [i.decode("utf-8") for i in np.unique(self.cfam_table.col("fam"))]

    def resizeEvent(self, event):
        """
        Updates the plot (if there is one) upon window resize.
        """
        super(InteractivePlotApp, self).resizeEvent(event)
        if self.plot_ready:
            if self.tab_widget.currentIndex() == 0:
                self.update_plot_N()
            elif self.tab_widget.currentIndex() == 1:
                self.update_plot_C()

    def select_all_gyro_N(self):
        """
        Selects all gyromagnetic ratios in the list to compare with ambiguous resonances from 15N.
        """
        for index in range(self.gyromagnetic_widget_N.count()):
            item = self.gyromagnetic_widget_N.item(index)
            item.setSelected(True)

    def clear_gyro_N(self):
        """
        Clears the selection of gyromagnetic ratios in the list to compare with ambiguous resonances from 15N.
        """
        self.gyromagnetic_widget_N.clearSelection()

    def select_all_items_C(self):
        """
        Selects all simulations for the 13C families to plot.
        """
        for index in range(self.families_widget.count()):
            item = self.families_widget.item(index)
            item.setSelected(True)

    def clear_selection_C(self):
        """
        Clears the selection of simulations for the 13C families to plot.
        """
        self.families_widget.clearSelection()

    def select_all_gyro_C(self):
        """
        Selects all gyromagnetic ratios in the list to compare with ambiguous resonances from 13C.
        """
        for index in range(self.gyromagnetic_widget_C.count()):
            item = self.gyromagnetic_widget_C.item(index)
            item.setSelected(True)

    def clear_gyro_C(self):
        """
        Clears the selection of gyromagnetic ratios in the list to compare with ambiguous resonances from 13C.
        """
        self.gyromagnetic_widget_C.clearSelection()

    def set_right_layout(self):
        """
        Intializes the plot on the right side of the grid with an empty plot.
        """
        self.fig = Figure(dpi=400)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.set_xlabel(r"$\tau$ ($\mu$s)")
        self.ax.set_xlim(0.05, 3)
        self.ax.set_ylim(0, 1)
        self.ax.set_ylabel("Transition Probability")

        self.canvas = FigureCanvas(self.fig)

        # Add a navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.right_layout.addWidget(self.toolbar)
        self.right_layout.addWidget(self.canvas)

    def select_file_N(self):
        """
        Select the experimental data file.
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            if selected_file:
                self.expt_filename_N = selected_file
                self.expt_file_label_N.setText(f"File: {os.path.basename(selected_file)}")

    def select_file_C(self):
        """
        Select the experimental data file.
        """
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            if selected_file:
                self.expt_filename_C = selected_file
                self.expt_file_label_C.setText(f"File: {os.path.basename(selected_file)}")

    def gyro_key_map(self, key):
        return key.removeprefix("<sup>").split("</sup>")

    def update_plot_N(self):
        """
        Update the plot with the selected parameters.

        The params for the plot are read from the widgets and then the corresponding time series is fetched from the dataset.
        A second curve is added if experimental data is supplied as well. Lastly, the `plot_ready` param is set as `True` to handle window resizes.
        """
        self.ax.clear()

        selected_ms = int(self.ms_widget_N.currentText())
        selected_M = int(self.M_widget_N.currentText())
        selected_B0 = float(self.B0_widget_N.currentText())
        selected_theta = self.theta_widget_N.currentText()
        selected_gyromagnetic = [
            item.data(Qt.UserRole) for item in self.gyromagnetic_widget_N.selectedItems()
        ]

        XY8 = self.N15_table.read_where(
            f"(order=={selected_M}) & (field=={selected_B0}) & (field_angle=={selected_theta}) & (ms=={selected_ms})"
        )

        selected_unit_id = self.unit_btngrp_N.checkedId()
        unit_list = [1e3, 1, 1e-3, 1e-6]
        unit_label_t = [
            r"$\tau$ (ns)",
            r"$\tau$ ($\mu$s)",
            r"$\tau$ (ms)",
            r"$\tau$ (s)",
        ]
        unit_label_f = ["f (GHz)", "f (MHz)", "f (kHz)", "f (Hz)"]

        if XY8.size == 0:
            self.ax.text(
                0.5,
                0.5,
                "Simulation results are not available yet for these values",
                horizontalalignment="center",
                verticalalignment="center",
                transform=self.ax.transAxes,
                bbox=dict(facecolor="yellow", alpha=0.5, edgecolor="black"),
            )
        else:
            XY8 = XY8["data"][0]
            x_axis = (
                self.freq / unit_list[selected_unit_id]
                if self.radio2_N.isChecked()
                else self.tau * unit_list[selected_unit_id]
            )
            self.ax.plot(
                x_axis,
                XY8,
                linewidth=1,
                label="Sim",
                color="#BD7D55",
                alpha=0.8,
            )

        # Plot experimental data if selected
        if self.expt_chkbox_N.isChecked() and self.expt_filename_N != "":
            exp_data = np.loadtxt(self.expt_filename_N, delimiter="\t")

            p = exp_data[:, 1] - min(exp_data[:, 1])

            self.ax.scatter(
                exp_data[:, 0],
                p * np.max(XY8) / np.max(p),
                color="#557DBD",
                s=0.2,
                alpha=0.7,
                label="Exp",
            )

        else:
            pass

        # Plot vertical lines for the gyromagnetic ratios chosen
        if selected_B0 != 0:
            for idx, val in enumerate(selected_gyromagnetic):
                # gyromagnetic ratios are stored in terms of MHz/T, so we correct for that
                # further, the fields are in mT, so we convert it to T
                pos = 1 / (
                    2 * self.gyromagnetic_ratios[val] / unit_list[selected_unit_id] * selected_B0 * 1e-3
                )
                if self.radio2_N.isChecked():
                    pos = 1 / 2 / pos
                gyro_label = self.gyro_key_map(val)
                self.ax.axvline(
                    x=pos,
                    linestyle="--",
                    linewidth=1,
                    label=rf"$^{{{gyro_label[0]}}}${gyro_label[1]}",
                    color=colors[idx + 1],
                )
        elif selected_B0 == 0 and len(selected_gyromagnetic) != 0:
            B0err = QMessageBox(self)
            B0err.setText("B<sub>0</sub> can not be 0 for comparison with γ")
            B0err.setWindowTitle("Cannot divide by zero")
            B0err.exec()

        x_axis_label = (
            unit_label_f[selected_unit_id] if self.radio2_N.isChecked() else unit_label_t[selected_unit_id]
        )
        self.ax.set_xlabel(x_axis_label)
        self.ax.set_ylabel("Transition Probability")
        self.ax.set_title(rf"XY8-{selected_M}, $B_0=${selected_B0} mT, $\theta=${selected_theta}$^\circ$")

        # plot the arXiv reference
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        self.ax.text(
            x_min + (x_max - x_min) * 0.01,
            y_max - (y_max - y_min) * 0.01,
            "arXiv:2407.09411 [quant-ph]",
            fontsize=3,
            color="black",
            ha="left",
            va="top",
            alpha=0.6,
        )

        self.ax.legend()
        self.fig.tight_layout()

        self.canvas.draw()
        self.plot_ready = True

    def update_plot_C(self):
        """
        Update the plot with the selected parameters.

        The params for the plot are read from the widgets and then the corresponding time series is fetched from the dataset.
        A second curve is added if experimental data is supplied as well. Lastly, the `plot_ready` param is set as `True` to handle window resizes.
        """
        self.ax.clear()

        selected_ms = int(self.ms_widget_C.currentText())
        selected_M = int(self.M_widget_C.currentText())
        selected_B0 = float(self.B0_widget_C.currentText())
        selected_gyromagnetic = [
            item.data(Qt.UserRole) for item in self.gyromagnetic_widget_C.selectedItems()
        ]

        selected_unit_id = self.unit_btngrp_C.checkedId()
        unit_list = [1e3, 1, 1e-3, 1e-6]
        unit_label_t = [
            r"$\tau$ (ns)",
            r"$\tau$ ($\mu$s)",
            r"$\tau$ (ms)",
            r"$\tau$ (s)",
        ]
        unit_label_f = ["f (GHz)", "f (MHz)", "f (kHz)", "f (Hz)"]

        selected_fam = [item.text() for item in self.families_widget.selectedItems()]

        for fam in selected_fam:
            XY8 = self.C13_table.read_where(
                f"(order=={selected_M}) & (fam==b'{fam}') & (field=={selected_B0}) & (ms=={selected_ms})"
            )
            if XY8.size == 0:
                self.ax.text(
                    0.5,
                    0.5,
                    "Simulation results are not available yet for these values",
                    horizontalalignment="center",
                    verticalalignment="center",
                    transform=self.ax.transAxes,
                    bbox=dict(facecolor="yellow", alpha=0.5, edgecolor="black"),
                )
            else:
                XY8 = XY8["data"][0]
                x_axis = (
                    self.freq / unit_list[selected_unit_id]
                    if self.radio2_C.isChecked()
                    else self.tau * unit_list[selected_unit_id]
                )
                self.ax.plot(
                    x_axis,
                    XY8,
                    linewidth=1,
                    label=fam,
                    alpha=0.8,
                )

        if self.expt_chkbox_C.isChecked() and self.expt_filename_C != "":
            exp_data = np.loadtxt(self.expt_filename_C, delimiter="\t")

            p = exp_data[:, 1] - min(exp_data[:, 1])

            self.ax.scatter(
                exp_data[:, 0],
                p * np.max(XY8) / np.max(p),
                color="#557DBD",
                s=0.2,
                alpha=0.7,
                label="Exp",
            )

        else:
            pass

        # Plot vertical lines for the gyromagnetic ratios chosen
        if selected_B0 != 0:
            for idx, val in enumerate(selected_gyromagnetic):
                # gyromagnetic ratios are stored in terms of MHz/T, so we correct for that
                # further, the fields are in mT, so we convert it to T
                pos = 1 / (
                    2 * self.gyromagnetic_ratios[val] / unit_list[selected_unit_id] * selected_B0 * 1e-3
                )
                if self.radio2_C.isChecked():
                    pos = 1 / 2 / pos
                gyro_label = self.gyro_key_map(val)
                self.ax.axvline(
                    x=pos,
                    linestyle="--",
                    linewidth=1,
                    label=rf"$^{{{gyro_label[0]}}}${gyro_label[1]}",
                    color=colors[idx + 1],
                )
        elif selected_B0 == 0 and len(selected_gyromagnetic) != 0:
            B0err = QMessageBox(self)
            B0err.setText("B<sub>0</sub> can not be 0 for comparison with γ")
            B0err.setWindowTitle("Cannot divide by zero")
            B0err.exec()

        x_axis_label = (
            unit_label_f[selected_unit_id] if self.radio2_C.isChecked() else unit_label_t[selected_unit_id]
        )
        self.ax.set_xlabel(x_axis_label)
        self.ax.set_ylabel("Transition Probability")
        self.ax.set_title(rf"XY8-{selected_M}, $B_0=${selected_B0} mT")

        # plot the arXiv reference
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        self.ax.text(
            x_min + (x_max - x_min) * 0.01,
            y_max - (y_max - y_min) * 0.01,
            "arXiv:2407.09411 [quant-ph]",
            fontsize=3,
            color="black",
            ha="left",
            va="top",
            alpha=0.6,
        )

        self.ax.legend()
        self.fig.tight_layout()

        self.canvas.draw()
        self.plot_ready = True


if __name__ == "__main__":
    app = QApplication()
    window = InteractivePlotApp()
    window.show()
    sys.exit(app.exec())
