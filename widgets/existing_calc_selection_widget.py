import logging
import logging.config
from os import path
import datetime
from dateutil.relativedelta import relativedelta
from bokeh.plotting import figure
from bokeh.models import DatetimeTickFormatter
import panel as pn
import param
from calculations.database_queries import get_flow_meta_data, get_flow_ts_from_id #update_data
#import pandas as pd
#import numpy as np
#from bokeh.layouts import layout, column, row
#from bokeh.models import ColumnDataSource, TableColumn, DatetimeTicker, DatetimeTickFormatter
#from panel.widgets import Tabulator
#from functools import partial

logger = logging.getLogger(__name__)
logger.propagate = False


class ExistingCalcSelectionWidget(param.Parameterized):
    df = param.DataFrame()
    selected_data_name = param.String()
    selected_data_id = param.String()
    selected_indices = param.Integer()
    
    def __init__(self, open_modal_callback=None, **params):
        super().__init__(**params)
        self.df = get_flow_meta_data()
        self.open_modal_callback = open_modal_callback
        self.init_ui()

    def update_plot(self):
        self.plot.renderers.clear()
        self.plot.yaxis.axis_label = f"{self.df.loc[self.idx, 'unit']}"
        self.plot.title.text = f"{self.selected_data_id}, {self.df.loc[self.idx, 'name']}"
        self.plot.line(x=self.selected_data.index, y=self.selected_data, line_width=2)
        self.plot.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d")

    def load_ts_prev_month(self, event):
        new_start_time = self.start_time - relativedelta(months=1)
        if new_start_time <= datetime.datetime.now():
            self.start_time = new_start_time
            self.end_time = self.start_time + relativedelta(months=1) - datetime.timedelta(days=1)
            self.selected_data = get_flow_ts_from_id(self.selected_data_id, self.start_time, self.end_time)
            self.date_text.value = f"{self.start_time.strftime('%Y-%m-%d')} - {self.end_time.strftime('%Y-%m-%d')}"
            self.update_plot()

    def load_ts_next_month(self, event):
        new_start_time = self.start_time + relativedelta(months=1)
        if new_start_time <= datetime.datetime.now():
            self.start_time = new_start_time
            self.end_time = self.start_time + relativedelta(months=1) - datetime.timedelta(days=1)
            self.selected_data = get_flow_ts_from_id(self.selected_data_id, self.start_time, self.end_time)
            self.date_text.value = f"{self.start_time.strftime('%Y-%m-%d')} - {self.end_time.strftime('%Y-%m-%d')}"
            self.update_plot()

    def selection_handler(self, event):
        self.idx = event.row
        idx = event.row
        self.selected_data_id = str(self.df.loc[idx, "unique_id"])
        self.selected_data_name = self.df.loc[idx, 'name']
        self.calc_type = self.df.loc[idx, 'calc_type']
        self.original_signal_id = str(self.df.loc[idx, "original_signal_id"])

        # not shown
        self.diameter = self.df.loc[idx, 'diameter']
        self.roughness = self.df.loc[idx, 'roughness']
        self.slope = self.df.loc[idx, 'slope']
        self.ski_width = self.df.loc[idx, 'ski_width']
        self.ski_height = self.df.loc[idx, "ski_height"]
        self.unit = self.df.loc[idx, 'unit']

        now = datetime.datetime.now()
        self.start_time = (now - relativedelta(months=1))
        self.end_time = now
        self.selected_data = get_flow_ts_from_id(self.selected_data_id, self.start_time, self.end_time)

        self.plot.renderers.clear()
        self.plot.line(x=self.selected_data.index, y=self.selected_data, line_width=2)
        self.plot.title.text = f"{self.selected_data_id}, {self.df.loc[idx, 'name']}"
        self.plot.yaxis.axis_label = f"{self.df.loc[idx, 'unit']}"
        self.plot.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d")

        column = event.column
        if column == 'Edit':
            button_clicked = event.value
            print(button_clicked)
            print(f"Print button clicked in row {idx}")
            if self.calc_type == "overfall":
                self.open_modal_callback(event, modal_type='modal_2', 
                                         input_data=(
                                             self.selected_data,
                                             self.selected_data_name,
                                             self.selected_data_id,
                                             "overfall",
                                             self.unit,
                                             self.original_signal_id,
                                             (self.ski_width, self.ski_height)))

            if self.calc_type == "rorberakning":
                self.open_modal_callback(event, modal_type='modal_2',
                                         input_data=(
                                             self.selected_data,
                                             self.selected_data_name,
                                             self.selected_data_id,
                                             "rorberakning",
                                             self.unit,
                                             self.original_signal_id,
                                             (self.slope, self.diameter, self.roughness)))

    def init_ui(self):
        empty_plot = figure(title="",
                            min_width=200, height=300, 
                            sizing_mode="scale_width",)
        self.plot = empty_plot

        backward = pn.widgets.Button(name='\u25c0', width=50)
        forward = pn.widgets.Button(name='\u25b6', width=50)
        backward.on_click(self.load_ts_prev_month)
        forward.on_click(self.load_ts_next_month)
        self.date_text = pn.widgets.StaticText(value='-')

        header_filters = {
            'unique_id': {'type': 'input', 'func': 'like', 'placeholder': ''},
            'name': {'type': 'input', 'func': 'like', 'placeholder': ''},
            'original_signal_id': {'type': 'input', 'func': 'like',
                                   'placeholder': ''},
            'calc_type': {'type': 'list', 'func': 'in', 'valuesLookup': True,
                          'sort': 'asc', 'multiselect': True},
            'unit': {'type': 'list', 'func': 'in', 'valuesLookup': True,
                     'sort': 'asc', 'multiselect': True}
        }

        df_widget = pn.widgets.Tabulator(
            self.df[['unique_id', 'name', "original_signal_id",
                     'calc_type', "unit"]],
            show_index=False,
            min_width=200,
            height=600,
            sizing_mode="scale_width",
            buttons={'Edit': "<b style='color:Green !important;'>Redigera</b>"},
            disabled=True,  # Make cells non-editable
            header_filters=header_filters,
            titles={'unique_id': 'ID',
                    'name': 'Namn',
                    'original_signal_id': 'Insignal ID',
                    'calc_type': 'Beräkningstyp',
                    'unit': 'Enhet'}
        )
        df_widget.on_click(self.selection_handler)

        self.layout = pn.Row(
            df_widget,
            pn.Column(self.plot, pn.Row(backward, self.date_text, forward))
        )