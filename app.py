
from shiny import App, reactive, render, ui

from shinywidgets import render_plotly

import definitions.layout_styles as styles
from definitions.backend_funcs import detect_models, compute_overlap, plot_overlap

from definitions.ui_funcs import single_result_ui, update_single_result, overlap_page

# ======================================================================================================================

app_ui = ui.page_fillable(
    ui.page_navbar(
        ui.nav_spacer(),
        ui.nav_panel('Select input',
                     'Welcome to BrainMApp',
                     ui.input_text("results_folder",
                                   "Copy the path to the directory where your project results are stored"),
                     ui.input_action_button(id='go_button',
                                            label='GO',
                                            class_='btn btn-dark action-button'),
                     ' ',  # Spacer
                     ui.output_text(id='output_results_folder'),
                     # ui.output_ui(id='tryui'),
                     value='tab1'
                     ),
        ui.nav_panel('Main results',
                     ' ',  # Spacer - fix with padding later or also never
                     single_result_ui('result1'),
                     single_result_ui('result2'),
                     ' ',  # Spacer
                     value='tab2'
                     ),
        ui.nav_panel('Overlap',
                     'Welcome to BrainMApp',  # Spacer - fix with padding later or also never
                     overlap_page,
                     ' ',  # spacer
                     value='tab3'
                     ),
        title="BrainMApp: visualize your verywise output",
        selected='tab1',
        position='fixed-top',
        fillable=True,
        bg='white',
        window_title='BrainMApp',
        id='navbar'),

    padding=styles.PAGE_PADDING,
    gap=styles.PAGE_GAP,
)


def server(input, output, session):

    model1, term1 = update_single_result('result1', go=input.go_button, input_resdir=input.results_folder)
    model2, term2 = update_single_result('result2', go=input.go_button, input_resdir=input.results_folder)

    @output
    @render.text
    @reactive.event(input.go_button)
    def output_results_folder():
        return input.results_folder()

    # @render.ui
    # @reactive.event(input.go_button)
    # def tryui():
    #     models = detect_models(resdir=input.results_folder(), out_clean=False)
    #     return ui.input_selectize(
    #         id='select_model',
    #         label='Choose model',
    #         choices=models,
    #         selected=None)

    @render.text
    def overlap_info():
        ovlp_info = compute_overlap(resdir=input.results_folder(),
                                    model1=model1(), term1=term1(),
                                    model2=model2(), term2=term2())[0]

        text = {}
        legend = {}
        for key in [1, 2, 3]:
            text[key] = f'**{ovlp_info[key][1]}%** ({ovlp_info[key][0]} vertices)' if key in ovlp_info.keys() else \
                '**0%** (0 vertices)'
            color = styles.OVLP_COLORS[key-1]
            legend[key] = f'<span style = "background-color: {color}; color: {color}"> oo</span>'

        return ui.markdown(f'There was a {text[3]} {legend[3]} **overlap** between the terms selected:</br>'
                           f'{text[1]} was unique to {legend[1]}  **{term1()}** (from the <ins>{model1()}</ins> model)</br>'
                           f'{text[2]} was unique to {legend[2]}  **{term2()}** (from the <ins>{model2()}</ins> model)')

    @reactive.Calc
    def overlap_brain3D():
        return plot_overlap(resdir=input.results_folder(),
                            model1=model1(), term1=term1(),
                            model2=model2(), term2=term2(),
                            surf=input.overlap_select_surface(),
                            resol=input.overlap_select_resolution())

    @render_plotly
    def overlap_brain_left():
        brain = overlap_brain3D()
        return brain['left']

    @render_plotly
    def overlap_brain_right():
        brain = overlap_brain3D()
        return brain['right']


app = App(app_ui, server)

