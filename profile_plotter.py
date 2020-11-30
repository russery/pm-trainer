import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import PySimpleGUI as sg
import numpy as np
from workout_profile import Workout


ZONES = [0, 0.75, 0.9,1.05,1.2,100]
ZONE_COLORS = ["blue", "green", "yellow", "orange", "red"]

def _get_zone(power):
	for i in range (0,len(ZONES)-1):
		print(i)
		if (power > ZONES[i]) and (power <= ZONES[i+1]):
			return i
	return None


if __name__ == '__main__':
	workout = Workout("workouts/short_stack.yaml")
	all_blocks = workout.get_all_blocks()
	plt.axes()


	dur = 0
	for block in all_blocks:
		print (block)
		width = block[0]
		start = block[1]
		end = block[2]
		zone = _get_zone(np.average([start,end]))
		color = ZONE_COLORS[zone]
		if start == end:
			# Start == end, so this is a rectangle
			shape = plt.Rectangle((dur, 0), width, start, fc=color)
		else:
			# This is a ramp (triangle)
			shape = plt.Polygon([[dur,0],[dur,start],[dur+width,end],[dur+width,0]],fc=color)
		plt.gca().add_patch(shape)
		dur += width

	plt.axis('scaled')


	fig = plt.gcf()
	figure_x, figure_y, figure_w, figure_h = fig.bbox.bounds


	def draw_figure(canvas, figure, loc=(0, 0)):
	    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
	    figure_canvas_agg.draw()
	    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)


	# define the window layout
	layout = [[sg.Text('Plot test', font='Any 18')],
	          [sg.Canvas(size=(figure_w, figure_h), key='canvas')],
	          [sg.OK(pad=((figure_w / 2, 0), 3), size=(4, 2))]]

	# create the form and show it without the plot
	window = sg.Window('Demo Application - Embedding Matplotlib In PySimpleGUI', layout, force_toplevel=True, finalize=True)

	# add the plot to the window
	fig_photo = draw_figure(window['canvas'].TKCanvas, fig)

	event, values = window.read()


