from shiny import Inputs, Outputs, Session, module, reactive, render, ui

from shinywidgets import output_widget, render_plotly

import definitions.layout_styles as styles
from definitions.backend_funcs import detect_models, extract_results, compute_overlap, \
    plot_surfmap, plot_overlap


@module.ui
def single_result_ui():

    model_choice = ui.output_ui('model_ui')

    term_choice = ui.output_ui('term_ui')

    output_choice = ui.input_selectize(
        id='select_output',
        label='Display',
        choices={'betas': 'Beta values', 'clusters': 'Clusters'},
        selected='betas')

    surface_choice = ui.input_selectize(
        id='select_surface',
        label='Surface type',
        choices={'pial': 'Pial', 'infl': 'Inflated', 'flat': 'Flat'},
        selected='pial')

    resolution_choice = ui.input_selectize(
        id='select_resolution',
        label='Resolution',
        choices={'fsaverage': 'High (164k nodes)', 'fsaverage6': 'Medium (50k nodes)', 'fsaverage5': 'Low (10k modes)'},
        selected='fsaverage6')

    update_button = ui.div(ui.input_action_button(id='update_button',
                                                  label='UPDATE',
                                                  class_='btn btn-dark action-button'),
                           style='padding-top: 15px')

    return ui.div(
        # Selection pane
        ui.layout_columns(
            ui.layout_columns(
                model_choice, term_choice, output_choice, surface_choice, resolution_choice,
                col_widths=(3, 3, 2, 2, 2),  # negative numbers for empty spaces
                gap='30px',
                style=styles.SELECTION_PANE),
            update_button,
            col_widths=(11, 1)
        ),
        # Info
        ui.row(
            ui.output_ui('info'),
            style=styles.INFO_MESSAGE
        ),
        # Brain plots
        ui.layout_columns(
            ui.card('Left hemisphere',
                    output_widget('brain_left'),
                    full_screen=True),  # expand icon appears when hovering over the card body
            ui.card('Right hemisphere',
                    output_widget('brain_right'),
                    full_screen=True)
        ))

@module.server
def update_single_result(input: Inputs, output: Outputs, session: Session,
                         go, input_resdir) -> tuple:

    # resdir = reactive.value(input_resdir)

    @output

    @render.ui
    @reactive.event(go)
    def model_ui():
        models = list(detect_models(input_resdir()).keys())
        return ui.input_selectize(
            id='select_model',
            label='Choose model',
            choices=models,
            selected=models[0])  # start_model

    @render.ui
    def term_ui():
        mod = input.select_model()
        terms = list(detect_models(input_resdir())[mod].keys())
        return ui.input_selectize(
            id='select_term',
            label="Choose term",
            choices=terms,
            selected=terms[0])  # always switch to first term after intercept

    @render.text
    def info():
        min_beta, max_beta, mean_beta, n_clusters, _, _ = extract_results(resdir=input_resdir(),
                                                                          model=input.select_model(),
                                                                          term=input.select_term())
        l_nc = int(n_clusters[0])
        r_nc = int(n_clusters[1])

        return ui.markdown(
            f'**{l_nc+r_nc}** clusters identified ({l_nc} in the left and {r_nc} in the right hemisphere).<br />'
            f'Mean beta value [range] = **{mean_beta:.2f}** [{min_beta:.2f}; {max_beta:.2f}]')

    @reactive.Calc
    @reactive.event(input.update_button, ignore_none=False)
    def brain3D():
        return plot_surfmap(resdir=input_resdir(),
                            model=input.select_model(),
                            term=input.select_term(),
                            surf=input.select_surface(),
                            resol=input.select_resolution(),
                            output=input.select_output())
    @render_plotly
    @reactive.event(input.update_button, ignore_none=False)
    def brain_left():
        brain = brain3D()
        return brain['left']

    @render_plotly
    @reactive.event(input.update_button, ignore_none=False)
    def brain_right():
        brain = brain3D()
        return brain['right']

    return input.select_model, input.select_term

# ------------------------------------------------------------------------------

overlap_page = ui.div(
        # Selection pane
        ui.layout_columns(
            ui.input_selectize(
                id='overlap_select_surface',
                label='Surface type',
                choices={'pial': 'Pial', 'infl': 'Inflated', 'flat': 'Flat'},
                selected='pial'),
            ui.input_selectize(
                id='overlap_select_resolution',
                label='Resolution',
                choices={'fsaverage': 'High (164k nodes)', 'fsaverage6': 'Medium (50k nodes)', 'fsaverage5': 'Low (10k modes)'},
                selected='fsaverage6'),

            ui.div(' ', style='padding-top: 80px'),

            col_widths=(3, 3, 2),  # negative numbers for empty spaces
            gap='30px',
            style=styles.SELECTION_PANE
        ),
        # Info
        ui.row(
            ui.output_ui('overlap_info'),
            style=styles.INFO_MESSAGE
        ),
        # Brain plots
        ui.layout_columns(
            ui.card('Left hemisphere',
                    output_widget('overlap_brain_left'),
                    full_screen=True),  # expand icon appears when hovering over the card body
            ui.card('Right hemisphere',
                    output_widget('overlap_brain_right'),
                    full_screen=True)
        ))

