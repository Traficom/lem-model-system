import pandas as pd
import re
import copy
from bokeh.plotting import figure, ColumnDataSource
from bokeh.io import output_file, show
from bokeh.models import Legend, FactorRange, NumeralTickFormatter
from bokeh.transform import factor_cmap
from bokeh.layouts import column
from pathlib import Path

scenario = "koko_suomi stored_speed"
submodel = "koko_suomi"
is_long_trips = True
result_path = \
    Path(f"C:/Users/kuivavee/Documents/Diplomityo_/Results/2018 main/koko_suomi")
plot_html_file_name = "Trip lengths vs HLT 2024_08_20_test_long.html"


"""Get modelled tour types"""
ms = pd.read_csv(result_path / 'mode_share.txt',
                 sep = '\t').fillna(0)
model_tour_types = sorted(list(set(ms['purpose'])))

"""Trip lengths import"""
trip_lengths = pd.read_csv(result_path / 'trip_lengths.txt',
                           sep = '\t',
                           index_col = 0).fillna(0)

if is_long_trips:
    length_classes = list(trip_lengths['interval'])[7:12]
else:
    length_classes = list(trip_lengths['interval'])[:7]

trip_lengths = trip_lengths.pivot_table(index = ['purpose', 'mode'],
                                        columns = 'interval').fillna(0)
trip_lengths.columns = trip_lengths.columns.droplevel()
trip_lengths = trip_lengths.reset_index()
trip_lengths.rename(columns = {'purpose': 'tour_type'}, inplace = True)

"""Trip length shares by tour type"""
trip_lengths_tt = trip_lengths.groupby(by = "tour_type").sum().reset_index().set_index("tour_type")
trip_lengths_tt = trip_lengths_tt.loc[model_tour_types,:]
trip_lengths_tt = trip_lengths_tt.set_index(trip_lengths_tt.index.astype(str)
                                  + '_model')

if is_long_trips:
    hlt_lengths = pd.read_csv("C:/Users/kuivavee/Documents/ConnectionTrips/lem-model-system/Scripts/dist_shares_long.csv",
                            sep = ',')
    hlt_lengths['w'] = hlt_lengths['w']/21
else:
    hlt_lengths = pd.read_csv( "C:/Users/kuivavee/Documents/ConnectionTrips/lem-model-system/Scripts/dist_sh_mode.csv",
                            sep = ',')
hlt_lengths = hlt_lengths[['tour_type', 'mode', 'dist_int', 'w']]\
                             .pivot_table(index = ['tour_type','mode'],
                                          columns = 'dist_int')
hlt_lengths.columns = hlt_lengths.columns.droplevel(0)
hlt_lengths = hlt_lengths.reset_index()                            

hlt_lengths_tt = hlt_lengths.groupby(by = "tour_type").sum().reset_index().set_index("tour_type")
hlt_lengths_tt = hlt_lengths_tt.loc[model_tour_types,:]
hlt_lengths_tt = hlt_lengths_tt.set_index(hlt_lengths_tt.index.astype(str)
                                  + '_HLT')

combined_data_tt = pd.concat([trip_lengths_tt, hlt_lengths_tt],
                          join = 'inner').fillna(0)

combined_data_shares_tt = combined_data_tt.div(combined_data_tt.sum(axis = 1), axis = 0)

"""Trip lengths overall"""

model_demand = trip_lengths_tt.transpose().sum(axis = 1).to_frame()
model_demand = model_demand.set_index(model_demand.index.astype(str)
                                      + '_model')
hlt_demand = hlt_lengths_tt.transpose().sum(axis = 1).to_frame()
hlt_demand = hlt_demand.set_index(hlt_demand.index.astype(str)
                                  + '_HLT')
                   
combined_demand = pd.concat([model_demand, hlt_demand],
                            join = 'inner')
combined_demand.columns = ['demand']

"""Trip length shares by mode and tour type"""

hlt_lengths_m = copy.deepcopy(hlt_lengths)
hlt_lengths_m['tt_mode'] = hlt_lengths_m['tour_type'] + "_" + hlt_lengths_m['mode']
hlt_lengths_m.set_index('tt_mode', inplace = True)

trip_lengths_m = copy.deepcopy(trip_lengths)
trip_lengths_m['tt_mode'] = trip_lengths_m['tour_type'] + "_" + trip_lengths_m['mode']
trip_lengths_m.set_index('tt_mode', inplace = True)
trip_lengths_m.index = trip_lengths_m.index.str.replace('car_leisure', 'car_drv')
trip_lengths_m.index = trip_lengths_m.index.str.replace('car_work', 'car_drv')
trip_lengths_m.index = trip_lengths_m.index.str.replace('transit_leisure', 'transit')
trip_lengths_m.index = trip_lengths_m.index.str.replace('transit_work', 'transit')

tt_m = trip_lengths_m.index.to_list()

trip_lengths_m = trip_lengths_m[length_classes]
hlt_lengths_m = hlt_lengths_m.loc[tt_m, trip_lengths_m.columns.to_list()]

trip_lengths_m = trip_lengths_m.set_index(trip_lengths_m.index.astype(str)
                                    + '_model')
hlt_lengths_m = hlt_lengths_m.set_index(hlt_lengths_m.index.astype(str)
                                  + '_HLT')

"""Trip length shares by mode"""

hlt_lengths_mm = copy.deepcopy(hlt_lengths_m)
trip_lengths_mm = copy.deepcopy(trip_lengths_m)

for tt in model_tour_types:
    hlt_lengths_mm.index = hlt_lengths_mm.index.str.replace(tt+"_", '')
    trip_lengths_mm.index = trip_lengths_mm.index.str.replace(tt+"_", '')
    
hlt_lengths_mm.index.name = "mode"
trip_lengths_mm.index.name = "mode"
hlt_lengths_mm = hlt_lengths_mm.groupby(by = "mode").sum().reset_index().set_index("mode")
trip_lengths_mm = trip_lengths_mm.groupby(by = "mode").sum().reset_index().set_index("mode")

if is_long_trips:
    modes = ['car_drv', 'car_pax', 'long_d_bus', 'train', 'airplane']
else:
    modes = ['car_drv', 'car_pax', 'transit', 'bike', 'walk']

"""PLOTTING"""

"""Trip length shares by tour type"""

output_file(f'./{plot_html_file_name}')
tour_types = model_tour_types
cols = [
'#ffff61',
'#ffc433',
'#ff6133',
'#ff0e0e',
'#f133ff',
#'#8b33ff',
'#0019ff',
'#0e9aff'
] 

factors = sum([[(t, "model"), (t, "HLT")]
               for t in tour_types], [])

data_columns = ['_'.join(i) for i in factors]
data_dict = combined_data_shares_tt.loc[data_columns,:].to_dict(orient = 'list')

factor_dict = dict(x = factors)
factor_dict.update(data_dict)
source = ColumnDataSource(data = factor_dict)

fig = figure(x_range = FactorRange(*factors),
             height = 500,
             width = 1200,
             title = "Trip length shares by tour type",
             toolbar_location = None,
             tools = "")

v = fig.vbar_stack(length_classes,
                   x = 'x',
                   width = 0.9,
                   alpha = 0.45,
                   line_alpha = 0.0,
                   color = cols[(len(cols)-len(length_classes)):],
                   source = source)

fig.y_range.start = 0
fig.y_range.end = 1
fig.x_range.range_padding = 0.1
fig.xaxis.major_label_orientation = 1
fig.xgrid.grid_line_color = None
fig.yaxis[0].formatter = NumeralTickFormatter(format = "0%")

legend = Legend(items = [(mode, [val])
                         for mode, val in zip(length_classes, v)],
                location = (5, 100))

fig.add_layout(legend, 'right')
fig.legend[0].items.reverse()

"""Demand by trip_length"""

factors_d = sum([[(t, "model"), (t, "HLT")]\
                 for t in length_classes], [])

data_columns_d = ['_'.join(i) for i in factors_d]
data_dict_d = combined_demand.loc[data_columns_d,:]\
                   .to_dict(orient = 'list')

factor_dict_d = dict(x = factors_d)
factor_dict_d.update(data_dict_d)
source_demand = ColumnDataSource(data = factor_dict_d)

fig3 = figure(x_range = FactorRange(*factors_d),
             height = 500,
             width = 500,
             title = "Demand by trip length (all tour types)",
             toolbar_location = None,
             tools = "")

v3 = fig3.vbar(x = 'x',
               top = 'demand',
               width = 0.9,
               alpha = 0.4,
               source = source_demand,
               line_color = "white",
               fill_color = factor_cmap('x',
                                        palette = ["orange", "blue"],
                                        factors = ["model", "HLT"],
                                        start = 1,
                                        end = 2))

fig3.y_range.start = 0
fig3.x_range.range_padding = 0.1
fig3.xaxis.major_label_orientation = 1
fig3.xgrid.grid_line_color = None
fig3.yaxis[0].formatter = NumeralTickFormatter(format = "0")

"""Trip lengths per tour type"""

def trip_lengths_per_tour_type(tour_type: str,
                               model_data: pd.DataFrame,
                               hlt_data: pd.DataFrame):
    
    model_demand = model_data.transpose()[tour_type+"_model"].to_frame()
    model_demand = model_demand.set_index(model_demand.index.astype(str)
                                        + '_model')
    model_demand.columns = [tour_type]
    hlt_demand = hlt_data.transpose()[tour_type+"_HLT"].to_frame()
    hlt_demand = hlt_demand.set_index(hlt_demand.index.astype(str)
                                    + '_HLT')
    hlt_demand.columns = [tour_type]
                    
    data = pd.concat([model_demand, hlt_demand],
                     join = 'inner')
    data.columns = ['demand']
    
    factors = sum([[(t, "model"), (t, "HLT")]\
                    for t in length_classes], [])

    data_columns = ['_'.join(i) for i in factors]
    data_dict = data.loc[data_columns,:]\
                    .to_dict(orient = 'list')

    factor_dict = dict(x = factors)
    factor_dict.update(data_dict)
    source_demand = ColumnDataSource(data = factor_dict)

    fig = figure(x_range = FactorRange(*factors),
                height = 500,
                width = 500,
                title = f"Demand by trip length ({tour_type})",
                toolbar_location = None,
                tools = "")

    v = fig.vbar(x = 'x',
                top = 'demand',
                width = 0.9,
                alpha = 0.4,
                source = source_demand,
                line_color = "white",
                fill_color = factor_cmap('x',
                                            palette = ["orange", "blue"],
                                            factors = ["model", "HLT"],
                                            start = 1,
                                            end = 2))

    fig.y_range.start = 0
    fig.x_range.range_padding = 0.1
    fig.xaxis.major_label_orientation = 1
    fig.xgrid.grid_line_color = None
    fig.yaxis[0].formatter = NumeralTickFormatter(format = "0")
    
    return fig

tour_type_figs = [trip_lengths_per_tour_type(tour_type = tt,
                                             model_data = trip_lengths_tt,
                                             hlt_data = hlt_lengths_tt)
                                             for tt in tour_types]

tour_type_mode_figs = [trip_lengths_per_tour_type(tour_type = tt,
                                                  model_data = trip_lengths_m,
                                                  hlt_data = hlt_lengths_m)
                                                  for tt in tt_m]

mode_figs = [trip_lengths_per_tour_type(tour_type = tt,
                                        model_data = trip_lengths_mm,
                                        hlt_data = hlt_lengths_mm)
                                        for tt in modes]

show(column(children = [fig, fig3] + tour_type_figs + mode_figs + tour_type_mode_figs))