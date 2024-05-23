#import pandas as pd
#import numpy as np
import panel as pn
import logging
import logging.config
import os
import datetime
from dateutil.relativedelta import relativedelta
from bokeh.models import Button, DatetimeTickFormatter, Tooltip
from bokeh.models.widgets import AutocompleteInput
from bokeh.plotting import figure
import folium
from folium.plugins import MarkerCluster
import param
from IPython.display import HTML, display
from calculations.database_queries import get_ts_from_id


logger = logging.getLogger(__name__)
logger.propagate = False

class SignalSelectionWidget(param.Parameterized):
    df = param.DataFrame()
    selected_data = param.DataFrame()
    selected_data_name = param.String()
    selected_data_id = param.String()
    selected_indices = param.Integer()
    selected_data_lat = param.Number()
    selected_data_long = param.Number()

    def __init__(self, df, open_modal_callback=None, **params):
        super().__init__(**params)
        self.df = df
        self.open_modal_callback = open_modal_callback
        self.init_ui()

    def selection_handler(self, attr, old, new):
        selected_value = new
        if selected_value[0]:
            idx = self.df[self.df['Search'] == selected_value].index[0]

            self.selected_data_name = self.df.loc[idx, 'name'] 
            self.selected_data_id = str(self.df.loc[idx, "SubjectID"])

            # choosing standard display plot time length
            now = datetime.datetime.now()
            self.start_time = (now - relativedelta(months=1))
            self.end_time = now

            self.selected_data = get_ts_from_id(self.selected_data_id, self.start_time, self.end_time)
            self.selected_indices = int(idx)

            coordinates = self.df.loc[idx, "coordinates"]
            self.update_plot()
            self.date_text.value = f"{self.start_time.strftime('%Y-%m-%d')} - {self.end_time.strftime('%Y-%m-%d')}"
            self.update_map(coordinates)

    def update_plot(self):
        self.plot.renderers.clear()
        self.plot.yaxis.axis_label = f"{self.df.loc[self.selected_indices, 'unit']}"
        self.plot.title.text = f"{self.selected_data_id}, {self.selected_data_name}"
        self.plot.line(x=self.selected_data.index, y=self.selected_data, line_width=2)
        self.plot.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d")

    def update_map(self, coordinates):
        m = folium.Map(location=[coordinates[0], coordinates[1]], zoom_start=14)
        self.marker_cluster = MarkerCluster().add_to(m)
        for idx, row in self.df.iterrows():
            color = 'orange' if row['coordinates'] == coordinates else 'blue'
            folium.Marker(location=row['coordinates'], popup=f"ID: {row['SubjectID']}", icon=folium.Icon(icon="tint", prefix='fa', color=color)).add_to(self.marker_cluster)
        self.folium_pane.object = m

        js = f"""
            <script>
            window.py_function = function(data) {{
                var point = JSON.parse(data);
                google.colab.kernel.invokeFunction('handle_click', [point]);
            }}
            </script>
            """
        # Display the JavaScript function in the output cell
        display(HTML(js))

    def marker_click_handler(self, location, popup):
        # Get the index of the row corresponding to the clicked marker
        idx = self.df[self.df['coordinates'] == (location[0], location[1])].index[0]

        # Update selected data
        name = self.df.loc[idx, 'names'] 
        idd = self.df.loc[idx, "SubjectID"]
        #time_series = self.df.loc[idx, "Time_series"] 

        #self.selected_data = time_series
        self.selected_data_name = name
        self.selected_data_id = str(idd)
        self.selected_indices = int(idx)

        # Update plot
        self.plot.renderers.clear()
        self.plot.title.text = f"{self.selected_data_id}, {self.selected_data_name}"
        #self.plot.line(x=list(range(len(self.selected_data))), y=time_series, line_width=2)

        # Update autocomplete box
        self.autocomplete_input.value = f"{self.selected_data_id} | {self.selected_data_name}"
        # Update marker color
        coordinates = self.df.loc[idx, "coordinates"]
        self.update_map(coordinates)

    def load_ts_prev_month(self, event):
        new_start_time = self.start_time - relativedelta(months=1)
        if new_start_time <= datetime.datetime.now():
            self.start_time = new_start_time
            self.end_time = self.start_time + relativedelta(months=1) - datetime.timedelta(days=1)
            self.selected_data = get_ts_from_id(self.selected_data_id, self.start_time, self.end_time)
            self.date_text.value = f"{self.start_time.strftime('%Y-%m-%d')} - {self.end_time.strftime('%Y-%m-%d')}"
            self.update_plot()

    def load_ts_next_month(self, event):
        new_start_time = self.start_time + relativedelta(months=1)
        if new_start_time <= datetime.datetime.now():
            self.start_time = new_start_time
            self.end_time = self.start_time + relativedelta(months=1) - datetime.timedelta(days=1)
            self.selected_data = get_ts_from_id(self.selected_data_id, self.start_time, self.end_time)
            self.date_text.value = f"{self.start_time.strftime('%Y-%m-%d')} - {self.end_time.strftime('%Y-%m-%d')}"
            self.update_plot()

        # Define Python function to handle the marker click
    def handle_click(self, coordinates):
        print("Clicked coordinates:", coordinates)

    def init_ui(self):
        # Autocomplete
        self.df['Search'] = self.df.apply(lambda x: f"{x['SubjectID']} | {x['name']} | {x['unit']} |{x['beskrivning']}", axis=1)
        completion_list = self.df['Search'].tolist()
        autocomplete_input = AutocompleteInput(completions=completion_list, title="Sök", case_sensitive=False,
                                                          search_strategy='includes', min_characters=0, max_completions=10)
        autocomplete_input.min_width = 500
        autocomplete_input.min_height = 30
        autocomplete_input.margin = 15
        autocomplete_input.sizing_mode = 'scale_width'
        autocomplete_input.on_change('value', self.selection_handler)


        # plot
        self.plot = figure(title='Sök efter mätare genom "Sök" och välj önskad data', 
                           width=600, height=350, margin=30, sizing_mode='stretch_width')#, x_axis_type="datetime")
        self.plot.line(x=[0], y=[0], line_width=0)
        self.plot.axis.axis_label_text_font_size = "9pt"

        # Button
        calc_button = Button(label="Skapa flödesberäkning", button_type="default", width=200, height=40, sizing_mode='fixed')
        calc_button.on_click(lambda event: self.open_modal_callback(event, modal_type='modal_1', input_data=(self.selected_data, self.selected_data_name, self.selected_data_id)))

        # Forward backwards buttons + label
        backward = pn.widgets.Button(name='\u25c0', width=50)
        forward = pn.widgets.Button(name='\u25b6', width=50)
        backward.on_click(self.load_ts_prev_month)
        forward.on_click(self.load_ts_next_month)
        self.date_text = pn.widgets.StaticText(value='-')

        # Map
        m = folium.Map(location=[57.70887, 11.974559999999997], zoom_start=14, min_height=1400, min_width=300)
        self.marker_cluster = MarkerCluster().add_to(m)

        # Här finns kod som kan användas för att implementera markers med karta
        # Add markers for all coordinates with blue color
        # for _, row in self.df.iterrows():
        #    marker = folium.Marker(location=row['coordinates'], popup=f"ID: {row['SubjectID']}", icon=folium.Icon(icon="tint", prefix='fa', color='blue')).add_to(self.marker_cluster)
        #     marker.add_to(self.marker_cluster)

        self.folium_pane = pn.pane.HTML(m._repr_html_(), min_height=1400, min_width=300, sizing_mode='stretch_width')

        # Create layout
        self.final_layout = pn.Column(autocomplete_input, pn.Row(backward, self.date_text, forward, calc_button), self.plot)
        self.layout = pn.Column(pn.Row(self.final_layout, self.folium_pane, pn.widgets.TooltipIcon(value=Tooltip(content="This is a tooltip using a bokeh.models.Tooltip", position="right"))))


       #     marker.js_on_click(f"""
#     var event = new CustomEvent('marker-click', {{ detail: {{ marker_id: '{marker_id}' }} }});
#    document.dispatchEvent(event);
# """)
