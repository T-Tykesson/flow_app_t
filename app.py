from bokeh.models import RadioButtonGroup, Div
from os import path
import panel as pn
import logging
import logging.config
from widgets.signal_selection_widget import SignalSelectionWidget
from widgets.existing_calc_selection_widget import ExistingCalcSelectionWidget
from widgets.calctype_selection_widget import (CreateNewCalculationWidget,
                                               EditCalculationWidget)
from calculations.database_queries import update_data

#import os
#import numpy as np
#import pandas as pd

#import sqlalchemy
#import bokeh as bokeh
#from bokeh.plotting import figure
#from bokeh.models.widgets import AutocompleteInput
#from bokeh.layouts import layout, column, row

logger = logging.getLogger(__name__)
logger.propagate = False

def show_modal_1(event, input_data):
    input_ts, input_data_name, input_data_id = input_data
    ui.modal[0].clear()
    ui.modal[0].append(CreateNewCalculationWidget(input_ts, input_data_name, input_data_id).layout)
    ui.open_modal()


def show_modal_2(event, input_data):
    short_timeseries, selected_data_name, selected_data_id, calc_type, unit, original_signal_id, parameters = input_data
    ui.modal[0].clear()
    ui.modal[0].append(EditCalculationWidget(short_timeseries, selected_data_name, selected_data_id, calc_type, unit, original_signal_id, parameters,).layout)
    ui.open_modal()


def open_modal_callback(event, modal_type, input_data):
    if modal_type == 'modal_1':
        show_modal_1(event, input_data)
    elif modal_type == 'modal_2':
        show_modal_2(event, input_data)


def my_panel_app():
    logging.info("New session created")

    def button_click_handler(attr, old, new):
        if new == 0:
            final_layout[1] = SignalSelectionWidget(df, open_modal_callback=open_modal_callback).layout
        else:
            final_layout[1] = ExistingCalcSelectionWidget(open_modal_callback=open_modal_callback).layout

    radio_button_group = RadioButtonGroup(
        labels=["Skapa beräkning", "Existerande beräkningar"],
        active=0,
        width=250,
        height=30)
    radio_button_group.on_change('active', button_click_handler)
    
    final_layout = pn.Column(radio_button_group,
                             SignalSelectionWidget(df, open_modal_callback=open_modal_callback).layout)

    ui.main.append(final_layout)
    ui.servable()

pn.extension('tabulator')
ui = pn.template.BootstrapTemplate(favicon="images/favicon2.png", 
                                   site="Flödesberäkningar?", 
                                   title="Självfallet!")
ui.modal.append(pn.Column())
logout = pn.widgets.Button(name='Logga ut', button_type='primary')
logout.js_on_click(code="""window.location.href = './logout'""")
div_session_timeout = Div(name='div_inactivity', text='')
ui.header.append(logout)
ui.header.append(div_session_timeout)
df = update_data()
my_panel_app()