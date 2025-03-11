# streamlit_app.py

import streamlit as st
from streamlit_sortables import sort_items
import pandas as pd
import plotly.express as px

def main():
    st.set_page_config(layout="wide")
    st.title("[Experimental] MABI Suggestions Measurement Dashboard")

    input_data_file = None
    if input_data_file is None:
        st.header('Upload File to Get Started')
        input_data_file = st.file_uploader(
            "Upload CSV", 
            type=["csv"],
        )
        if input_data_file is not None:
            input_data = (
                pd.read_csv(input_data_file)
                .assign(**{
                    'theme': lambda df: (
                        df
                        ['theme']
                        .str
                        .split('theme_', expand=True)
                        [1]
                        .fillna('all')
                    )
                })
            )
            themes = (
                ["all"] +
                input_data
                .query('theme != "all"')
                ['theme']
                .drop_duplicates()
                .to_list()
            )
            st.subheader("Data preview:")
            st.dataframe(input_data)

    if input_data_file is not None:
        st.header('Settings')
        with st.expander("Click to expand/collapse"):
            audience_names = list(
                input_data
                ['audience_name']
                .str
                .title()
                .unique()
            )
            st.write("Audience Names:", audience_names)
            audiences = (
                input_data
                .query('audience != "all"')
                ['audience']
                .drop_duplicates()
                .to_list()
            )
            st.write('Drag audiences to set the order of appearance in the dashboard:')
            sorted_audiences = sort_items(audiences)
            input_data_sorted = (
                input_data
                .assign(
                    audience=lambda df: pd.Categorical(
                        df['audience'],
                        categories=sorted_audiences + ['all'],
                        ordered=True
                    )
                )
            )
            timestep_types = (
                input_data_sorted
                ['timestep_type']
                .unique()
            )
            timestep_type = st.radio(
                "Select Timestep Type",
                options=timestep_types,
                index=0,
            )
        with st.container():
            theme = st.selectbox(
                "Select Theme",
                options=themes,
                index=0
            )

        aggregated_data = (
            input_data_sorted
            .query('timestep_type == @timestep_type')
            .query('theme == @theme')
            .assign(**{
                'se_squared': lambda df: df['se'] ** 2
            })
            .groupby(
                [
                    'suggestion_type',
                    'action_type',
                    'outcome_type',
                    'theme',
                    'audience_name',
                    'audience',
                    'timestep_type',
                    'timestep',
                    'variable',
                ],
                as_index=False,
                observed=True
            )
            .agg(**{
                'value': ('value', 'sum'),
                'lower_ci': ('lower_ci', 'sum'),
                'upper_ci': ('upper_ci', 'sum'),
                'se_squared': ('se_squared', 'sum'),
            })
            .assign(**{
                'se': lambda df: df['se_squared'] ** 0.5
            })
        )
        with st.container():
            try:
                audience_plot_data = (
                    aggregated_data
                    .query('variable.str.contains("observed")')
                )
            except Exception as e:
                st.error(f"Error loading CSV file: {e}")
                st.write("No data to display")
            audience_columns = st.columns(3, vertical_alignment='top')
            with audience_columns[0]:
                observed_suggestion_plot = px.bar(
                    (
                        audience_plot_data
                        .query('outcome_type == "nbrx"')
                        .query('variable == "observed_suggestion"')
                    ),
                    x='timestep',
                    y='value',
                    color='audience',
                    barmode='relative',
                    facet_col='audience_name',
                    title='Observed Suggestions Over Time',
                    labels={'value': 'Observed Suggestions', 'timestep': 'Timestep'},
                    height=600,
                )
                st.plotly_chart(observed_suggestion_plot)
                
            with audience_columns[1]:
                observed_action_plot = px.bar(
                    (
                        audience_plot_data
                        .query('variable == "observed_action"')
                    ),
                    x='timestep',
                    y='value',
                    color='audience',
                    barmode='relative',
                    facet_col='audience_name',
                    title='Observed Action Over Time',
                    labels={'value': 'Observed Actions', 'timestep': 'Timestep'},
                    height=600
                )
                st.plotly_chart(observed_action_plot)
            with audience_columns[2]:
                outcome_types = [
                    'nbrx',
                    'trx'
                ]
                outcome_type_tabs = st.tabs(outcome_types)
                for outcome_type, tab in zip(outcome_types, outcome_type_tabs):
                    with tab:
                        observed_outcome_plot = px.bar(
                            (
                                audience_plot_data
                                .query(f'outcome_type == "{outcome_type}"')
                                .query('variable == "observed_outcome"')
                            ),
                            x='timestep',
                            y='value',
                            color='audience',
                            barmode='relative',
                            facet_col='audience_name',
                            title=f'Observed Outcomes Over Time ({outcome_type})',
                            labels={'value': 'Observed Outcomes', 'timestep': 'Timestep'},
                            height=600
                        )
                        st.plotly_chart(observed_outcome_plot)

        with st.container():
            st.write('Theme:', theme)
            incrementality_data = (
                aggregated_data
                .query('variable.str.startswith("pct_incremental")')
            )
            
            with st.container():
                audience_name = st.radio(
                    'Select Audience Name',
                    options=audience_names,
                    index=0
                )
                incremental_action_col, incremental_outcome_col = st.columns(2)
             
                with incremental_action_col:
                    pct_incremental_action_plot = px.bar(
                        (
                            incrementality_data
                            .query('variable == "pct_incremental_predicted_action"')
                            .query('audience_name == @audience_name.lower()')
                        ),
                        x='timestep',
                        y='value',
                        # error_y='upper_ci',
                        # error_y_minus='lower_ci',
                        error_y='se',
                        color='audience',
                        barmode='group',
                        height=600,
                        facet_row='outcome_type',
                        title='Percent Incremental Predicted Action Over Time',
                        labels={'value': 'Percent Incremental Predicted Actions', 'timestep': 'Timestep'},
                        # width=600
                    )
                    st.plotly_chart(
                        pct_incremental_action_plot,
                        key=f'pct_incremental_action_plot'
                    )
                with incremental_outcome_col:
                    pct_incremental_outcome_plot = px.bar(
                        (
                            incrementality_data
                            .query('variable == "pct_incremental_predicted_outcome"')
                            .query('audience_name == @audience_name.lower()')
                        ),
                        x='timestep',
                        y='value',
                        color='audience',
                        barmode='group',
                        facet_row='outcome_type',
                        # error_y='upper_ci',
                        # error_y_minus='lower_ci',
                        error_y='se',
                        height=600,
                        title='Percent Incremental Predicted Outcome Over Time',
                        labels={'value': 'Percent Incremental Predicted Outcomes', 'timestep': 'Timestep'},
                        # width=600
                    )
                    st.plotly_chart(
                        pct_incremental_outcome_plot,
                        key=f'pct_incremental_outcome_plot_{outcome_type}_{audience_name}'
                    )
            st.write("**Components:**")
            with st.expander("Click to expand"):
                component_variables = [
                    'counterfactual_action',
                    'predicted_action',
                    'incremental_action',
                    'counterfactual_outcome',
                    'predicted_outcome',
                    'incremental_outcome',
                ]
                component_data = (
                    aggregated_data
                    .query('variable in @component_variables')
                    .assign(**{
                        'variable': lambda df: pd.Categorical(
                            df['variable'],
                            categories=component_variables,
                            ordered=True
                        )
                    })
                )
                with st.container():
                    component_columns = st.columns(
                        2,
                        vertical_alignment='top'
                    )
                    with component_columns[0]:
                        action_component_plot = px.bar(
                            (
                                component_data
                                .query('variable.str.contains("action")')
                                .query('audience_name == @audience_name.lower()')
                                .query('outcome_type == "nbrx"')
                            ),
                            x='timestep',
                            y='value',
                            color='audience',
                            barmode='group',
                            facet_row='variable',
                            error_y='se',
                            height=800,
                            title='Action Components Over Time',
                            labels={'value': 'Value', 'timestep': 'Timestep'},
                        )
                        st.plotly_chart(
                            action_component_plot,
                            key=f'action_component_plot_{audience_name}'
                        )
                    with component_columns[1]:
                        outcome_component_plot = px.bar(
                            (
                                component_data
                                .query('variable.str.contains("outcome")')
                                .query('audience_name == @audience_name.lower()')
                            ),
                            x='timestep',
                            y='value',
                            color='audience',
                            barmode='group',
                            facet_row='variable',
                            facet_col='outcome_type',
                            error_y='se',
                            height=800,
                            title='Outcome Components Over Time',
                            labels={'value': 'Value', 'timestep': 'Timestep'},
                        )
                        st.plotly_chart(    
                            outcome_component_plot,
                            key=f'outcome_component_plot_{audience_name}'
                        )

        with st.container():
            performance_columns = st.columns(3)
            performance_variables = [
                'quality',
                'action_performance_index',
                'outcome_performance_index',
            ]
            performance_data = (
                aggregated_data
                .query('variable in @performance_variables')
                .assign(**{
                    'variable': lambda df: pd.Categorical(
                        df['variable'],
                        categories=performance_variables,
                        ordered=True
                    )
                })
            )
            with performance_columns[0]:
                quality_plot = px.bar(
                    (
                        performance_data
                        .query('variable == "quality"')
                        .query('audience_name == @audience_name.lower()')
                    ),
                    x='timestep',
                    y='value',
                    color='audience',
                    barmode='group',
                    # error_y='se',
                    facet_row='audience',
                    facet_col='outcome_type',
                    title='Quality Over Time',
                    labels={'value': 'Quality', 'timestep': 'Timestep'},
                    height=800
                )
                st.plotly_chart(quality_plot)
            with performance_columns[1]:
                action_performance_plot = px.bar(
                    (
                        performance_data
                        .query('outcome_type == "nbrx"')
                        .query('variable == "action_performance_index"')
                        .query('audience_name == @audience_name.lower()')
                    ),
                    x='timestep',
                    y='value',
                    color='audience',
                    barmode='group',
                    # error_y='se',
                    facet_row='audience',
                    facet_col='outcome_type',
                    title='Action Performance Index Over Time',
                    labels={'value': 'Action Performance Index', 'timestep': 'Timestep'},
                    height=800
                )
                st.plotly_chart(action_performance_plot)
            with performance_columns[2]:
                outcome_performance_plot = px.bar(
                    (
                        performance_data
                        .query('variable == "outcome_performance_index"')
                        .query('audience_name == @audience_name.lower()')
                    ),
                    x='timestep',
                    y='value',
                    color='audience',
                    barmode='group',
                    # error_y='se',
                    facet_row='audience',
                    facet_col='outcome_type',
                    title='Outcome Performance Index Over Time',
                    labels={'value': 'Outcome Performance Index', 'timestep': 'Timestep'},
                    height=800
                )
                st.plotly_chart(outcome_performance_plot)

if __name__ == "__main__":
    main()