import numpy as np
import logging
import logging.config
import os
import datetime
from dateutil.relativedelta import relativedelta
import bokeh
import panel as pn
import param
from bokeh.layouts import column, row
from bokeh.plotting import figure
from bokeh.models import (Button, Div, TextInput, Paragraph, RadioGroup,
                          DatetimeTickFormatter)
from bokeh.models.widgets import AutocompleteInput
from calculations.database_queries import (update_data, get_ts_from_id,
                                           store_calc_metadata, store_calc_ts,
                                           dataframe_to_input_data,
                                           delete_data_by_id)
#from panel.widgets import Tabulator
#from functools import partial
#import pandas as pd
#import numpy as np
#import time
from calculations.flow_calculations import overfall


logger = logging.getLogger(__name__)
logger.propagate = False

class OverfallSubWidget(param.Parameterized):
    input_data = param.Parameter()
    input_data_name = param.String()
    input_data_id = param.String()

    selected_width = param.Number()
    selected_height = param.Number()
    selected_unit = param.String()
    selected_ID = param.String()
    selected_name = param.String()
    
    def __init__(self, input_data, input_data_name, input_data_id,
                 unit=None, calc_unique_id=None, calc_name=None,
                 ski_width=None, ski_height=None, edit_mode=False, **params):
        super().__init__(**params)
        self.input_data = input_data
        self.input_data_name = input_data_name
        self.input_data_id = input_data_id
        self.edit_mode = edit_mode
        self.init_ui()

        # Predecide input field values if optional parameters are provided
        if calc_unique_id:
            self.selected_ID = calc_unique_id
            self.ID_textbox.value = calc_unique_id
        if calc_name:
            self.selected_name = calc_name
            self.name_textbox.value = calc_name
        if unit:
            self.selected_unit = unit
            self.unit_button.active = 0 if unit == "m3/s" else 1
        if ski_width:
            self.selected_width = ski_width
            self.ski_width.value = str(ski_width)
        if ski_height:
            self.selected_height = ski_height
            self.ski_height.value = str(ski_height)

    def load_display(self, x):
        # function to activate / deactivate loading widget
        if(x=='on'):
            self.loading.value=True
            self.loading.visible=True
        if(x=='off'):
            self.loading.value=False
            self.loading.visible=False

    def convert_to_float(self, value):
        value = value.replace(',', '.')
        try:
            float_value = float(value)
            return float_value
        except ValueError:
            return None

    def autocomplete_selection(self, attr, old, new):
        selected_value = new
        if selected_value[0]:
            idx = self.df[self.df['Search'] == selected_value].index[0]

            self.input_data_name = self.df.loc[idx, 'name'] 
            self.input_data_id = str(self.df.loc[idx, "SubjectID"])

            # choosing standard display plot time length
            now = datetime.datetime.now()
            self.start_time = (now - relativedelta(months=1))
            self.end_time = now

            self.input_data = get_ts_from_id(self.input_data_id, self.start_time, self.end_time)
    
    def preview_button_callback(self, values):
        activated_index = self.unit_button.active
        self.selected_unit = self.unit_button.labels[activated_index]
        print(self.selected_unit)

        display_name = f"{self.input_data_id}, {self.input_data_name}" 
        time_series = self.input_data

        try:
            self.Q_data = overfall(time_series, self.convert_to_float(self.ski_height.value), self.convert_to_float(self.ski_width.value), self.selected_unit)

            self.graph.renderers.clear()
            self.graph.title.text = f"Flödesberäkning, {display_name}"
            self.graph.yaxis.axis_label = f"Flöde ({self.selected_unit})"
            self.graph.line(x=self.input_data.index, y=self.Q_data, line_width=2)
            self.graph.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d")

        except Exception as e:
            print(f"got exception! {e}")
            self.graph.renderers.clear()
            self.graph.line(x=list(range(len(time_series))), y=time_series, line_width=2)
            self.graph.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d")
            # self.graph.title.text = "Skriv in numeriska värden"

    def save_button_callback(self, values):
        self.load_display('on')
        self.confirm_button.disabled = True
        self.loading.name = "Skapar beräkning..."
        self.create_calculation(values)
        self.load_display('off')
        self.confirm_button.disabled = False

    def no_click_callback(self):
        # return to previous layout
        self.delete_button = Button(label="Radera beräkning", button_type = 'danger')
        self.delete_button.on_click(self.delete_are_you_sure)
        self.layout[2][1][1][1] = self.delete_button

    def delete_are_you_sure(self):
        textbox =  Div(text="<b style='color:black;'> OBS! Är du säker du vill radera beräkning?</b>")
        yes_box = Button(label="Ja, ta bort beräkning", button_type = 'danger') 
        no_box = Button(label="Nej, återgå", button_type = 'primary')
        yes_box.on_click(self.delete_calculation)
        no_box.on_click(self.no_click_callback)
        self.layout[2][1][1][1] = pn.Column(textbox, pn.Row(yes_box, no_box))

    def delete_calculation(self):
        self.load_display('on')
        self.loading.name = "Raderar beräkning..."
        try:
            delete_data_by_id(self.selected_ID)
            self.load_display('off')
            self.status_text.text = "<b style='color:black;'>Beräkning raderades</b>"
            self.no_click_callback()
        except Exeption as e:
            #print("Error:", e)
            self.load_display('off')
            self.status_text.text = "<b style='color:red;'>Ett fel uppstod. Beräkning kunde inte raderas. </b>"

    def create_calculation(self, values):
        input_var= np.array([str(self.ID_textbox.value), str(self.name_textbox.value), str(self.ski_height.value), str(self.ski_width.value)])
        if np.any(input_var==""):
            self.load_display('off')
            self.status_text.text = "<b style='color:red;'>Alla fällt är inte ifyllda. </b>"
            return
            
        try:
            if self.edit_mode: 
                delete_data_by_id(self.ID_textbox.value)
                # Om Id inte har blivit ändrat i fältet, radera den gamla beräkningen 
                # Om Id ändras tas inte den gamla beräkningen bort
        except:
            pass # ingen data att ta bort, nytt id

        try:
            print(self.input_data_id)
            full_data = get_ts_from_id(self.input_data_id, None, None, all_data=True)
            self.selected_unit = self.unit_button.labels[self.unit_button.active]

            Q_data = overfall(
                full_data, 
                self.convert_to_float(self.ski_height.value),
                self.convert_to_float(self.ski_width.value),
                self.selected_unit,
                dataframe=True
            )
            new_data = dataframe_to_input_data(Q_data, str(self.ID_textbox.value))
            self.loading.name = "Sparar beräkning, detta kan ta ett tag..."
            store_calc_metadata(
                str(self.ID_textbox.value),
                str(self.name_textbox.value),
                str(self.input_data_id),
                "overfall",
                str(self.selected_unit),
                (self.convert_to_float(self.ski_height.value),
                 self.convert_to_float(self.ski_width.value))
            )
            store_calc_ts(new_data)
            
            self.status_text.text = "<b style='color:green;'>Insättning lyckades</b>"

        except Exception as e:
            print("Error:", e)
            self.load_display('off')
            self.status_text.text = "<b style='color:red;'>Ett fel uppstod. Kontrollera att ID inte redan finns och att alla fält är ifyllda korrekt.</b>"

    def init_ui(self):
        # loading bar and text
        self.loading = pn.indicators.LoadingSpinner(value=False, name='Skapar beräkning...', width=50, height=50, visible=False)
        self.status_text = Div(text="")

        # image
        png_pane = pn.pane.Image('images/overfall3.png', width=300)

        # text input
        self.ski_height = TextInput(title="Skibordshöjd (m)", width=100)
        self.ski_width = TextInput(title="Skibordsbredd (m)", width=100)

        # Vald datanamn, knappar Överfall, rör
        title_text = Div(text=f"{self.input_data_id}, {self.input_data_name}")

        # Beteckning och namn
        self.ID_textbox = bokeh.models.TextInput(title="", width=319)
        ID_title = Paragraph(text='Beteckning (ID)', align='center')
        ID_layout = pn.Row(ID_title, self.ID_textbox) # row([ID_title, self.ID_textbox])

        self.name_textbox = TextInput(title="", width=295)
        name_title = Paragraph(text='Benämning (Namn)', align='center')
        name_layout = pn.Row(name_title, self.name_textbox)

        # Enhetsval
        self.unit_button = RadioGroup(labels=["m3/s", "l/s"], active=0, background='white') # borde lägga till self
        unitchoice_title = Paragraph(text='Val av enhet')
        unitchoice_layout = row([unitchoice_title, self.unit_button])

        # plot
        activated_index = self.unit_button.active
        activated_label = self.unit_button.labels[activated_index]
        self.graph = figure(min_width=300, height=150, margin=15, y_axis_label=f"Flöde ({activated_label})", sizing_mode="scale_width")

        # Uppdatera, spara knappar
        update_button = Button(label="Förhandsgranska beräkning")
        update_button.on_click(self.preview_button_callback)
        self.confirm_button = Button(label="Spara beräkning", button_type = 'primary') #button_type = 'success') #
        self.confirm_button.on_click(self.save_button_callback)

        if self.edit_mode:
            # autocomplete input
            self.df = update_data()
            self.df['Search'] = self.df.apply(lambda x: f"{x['SubjectID']} | {x['name']} | {x['unit']} |{x['beskrivning']}", axis=1)
            completion_list = self.df['Search'].tolist()
            autocomplete_input = AutocompleteInput(completions=completion_list, title="Ändra insignal:", case_sensitive=False,
                                                              search_strategy='includes', min_characters=0, max_completions=10)
            autocomplete_input.min_width = 500
            autocomplete_input.min_height = 30
            autocomplete_input.margin = 15
            autocomplete_input.sizing_mode = 'scale_width'
            autocomplete_input.on_change('value', self.autocomplete_selection)

            # uppdatering av layout
            self.confirm_button.label = "Spara ändringar"
            self.confirm_button.button_type = "success"

            self.delete_button = Button(label="Radera beräkning", button_type = 'danger') #button_type = 'success') #
            self.delete_button.on_click(self.delete_are_you_sure) 
            # TODO: se till att få upp ytterligare valmöjlighet

            options_column = pn.Row(
                pn.Column(ID_layout, name_layout, unitchoice_layout),
                pn.Column(update_button, pn.Row(self.confirm_button, self.delete_button)),
                pn.Column(self.loading, self.status_text)
            )
            # slutgiltig layout
            self.layout = pn.Column(
                autocomplete_input,
                pn.Row(pn.Row(png_pane, pn.Column(self.ski_height, self.ski_width)), self.graph),
                options_column, #status_column, self.loading
            )
        else:
            options_column = pn.Row(
                pn.Column(ID_layout, name_layout, unitchoice_layout),
                pn.Column(update_button, self.confirm_button),
                pn.Column(self.loading, self.status_text)
            )
            self.layout = pn.Column(
                title_text,
                pn.Row(pn.Row(png_pane, pn.Column(self.ski_height, self.ski_width)), self.graph),
                options_column, #status_column, self.loading
            )