from  pyecharts.charts import Bar, Timeline
from pyecharts.globals import ThemeType
from pyecharts.options import LabelOpts
bar1 = Bar()
bar1.add_xaxis(["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"])
bar1.add_yaxis("商家A", [55, 40, 36, 40, 25, 80], label_opts=LabelOpts(position="right"))
bar1.reversal_axis()

bar2 = Bar()
bar2.add_xaxis(["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"])
bar2.add_yaxis("商家B", [15, 10, 16, 80, 20, 20], label_opts=LabelOpts(position="right"))
bar2.reversal_axis()

bar3 = Bar()
bar3.add_xaxis(["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"])
bar3.add_yaxis("商家C", [10, 30, 46, 40, 50, 30], label_opts=LabelOpts(position="right"))
bar3.reversal_axis()

timeline = Timeline({"theme":ThemeType.ESSOS})
timeline.add(bar1, "商家A")
timeline.add(bar2, "商家B")
timeline.add(bar3, "商家C")

timeline.add_schema(is_auto_play=True, play_interval=500,  is_loop_play=True)

timeline.render("商家.html")

dict_coa ={}
if 1966 in dict_coa.keys():
    dict_coa[1966].append(["1", "2"])
else:
    dict_coa[1966] = [["1", "2"]]

