import logging
import logging.config
import os
import panel as pn
import param
from bokeh.models import RadioButtonGroup
from widgets.overfall_subwidget import OverfallSubWidget
from widgets.pipeflow_subwidget import PipeflowSubWidget
#from calculations.flow_calculations import cole_white_flow_calc, overfall
#from calculations.database_queries import update_data, get_ts_from_id, store_calc_metadata, store_calc_ts, dataframe_to_input_data, delete_data_by_id
#import pandas as pd

#import numpy as np
#import time
#import datetime
#from dateutil.relativedelta import relativedelta
#import bokeh
#from bokeh.layouts import layout, column, row
#from bokeh.plotting import figure
#from bokeh.models import (ColumnDataSource, TableColumn, DataTable, CustomJS, Button, RadioButtonGroup, Div, 
# TextInput, Paragraph, RadioGroup, DatetimePicker, DatetimeTicker, DatetimeTickFormatter)
#from bokeh.models.widgets import AutocompleteInput
#from panel.widgets import Tabulator
#from functools import partial


logger = logging.getLogger(__name__)
logger.propagate = False

class CreateNewCalculationWidget(param.Parameterized):
    input_data = param.Parameter()
    input_data_name = param.String()
    input_data_id = param.String()

    def __init__(self, input_data, input_data_name, input_data_id,  **params):
        super().__init__(**params)
        self.input_data = input_data
        self.input_data_name = input_data_name
        self.input_data_id = input_data_id
        self.init_ui()

    def update_flow_type(self, attr, old, new):
        if new == 0:
            self.layout[1] = OverfallSubWidget(
                self.input_data,
                self.input_data_name,
                self.input_data_id,
            ).layout

        else:
            self.layout[1] = PipeflowSubWidget(
                self.input_data,
                self.input_data_name,
                self.input_data_id,
            ).layout

    def init_ui(self):
        radio_button_group = RadioButtonGroup(
            labels=["Överfallsberäkning", "Rörberäkning"],
            active=0,  width=250, height=30)

        radio_button_group.on_change('active', self.update_flow_type)
        self.layout = pn.Column(
            radio_button_group, 
            OverfallSubWidget(self.input_data,
                              self.input_data_name,
                              self.input_data_id,).layout
        )


class EditCalculationWidget(param.Parameterized):
    input_data = param.Parameter()
    input_data_name = param.String()
    input_data_id = param.String()

    def __init__(self, input_data, input_data_name, input_data_id, calc_type,
                 unit, original_signal_id, parameters, **params):
        super().__init__(**params)
        self.input_data = input_data
        self.input_data_name = input_data_name
        self.input_data_id = input_data_id
        self.calctype = calc_type
        self.unit = unit
        self.original_signal_id = original_signal_id
        self.parameters = parameters

        if calc_type == "overfall":
            self.ski_width, self.ski_height = parameters
        if calc_type == "rorberakning":
            self.slope, self.diameter, self.roughness = parameters

        self.init_ui()

    def update_flow_type(self, attr, old, new):
        if new == 0:
            self.layout[1] = OverfallSubWidget(
                self.input_data,
                self.input_data_name,
                self.original_signal_id,
                unit=self.unit,
                calc_unique_id=self.input_data_id,
                calc_name=self.input_data_name,
                edit_mode=True).layout

        else:
            self.layout[1] = PipeflowSubWidget(
                self.input_data,
                self.input_data_name,
                self.original_signal_id,
                unit=self.unit,
                calc_unique_id=self.input_data_id,
                calc_name=self.input_data_name,
                edit_mode=True
            ).layout

    def init_ui(self):
        radio_button_group = RadioButtonGroup(labels=["Överfallsberäkning",
                                                      "Rörberäkning"],
                                              active=0,  width=250, height=30)
        radio_button_group.on_change('active', self.update_flow_type)

        if self.calctype == "overfall":
            self.layout = pn.Column(
                radio_button_group,
                OverfallSubWidget(
                    self.input_data,
                    self.input_data_name,
                    self.input_data_id,
                    unit=self.unit,
                    calc_unique_id=self.input_data_id,
                    calc_name=self.input_data_name,
                    ski_width=self.ski_width,
                    ski_height=self.ski_height,
                    edit_mode=True
                ).layout)

        if self.calctype == "rorberakning":
            self.layout = pn.Column(
                radio_button_group,
                PipeflowSubWidget(
                    self.input_data,
                    self.input_data_name,
                    self.input_data_id,
                    unit=self.unit,
                    calc_unique_id=self.input_data_id,
                    calc_name=self.input_data_name,
                    slope=self.slope,
                    diameter=self.diameter,
                    roughness=self.roughness,
                    edit_mode=True
                ).layout)
