"""Visualization module for UT Austin grade distribution dashboard."""

from pathlib import Path

import altair as alt
import pandas as pd

# Disable row limit for large datasets
alt.data_transformers.disable_max_rows()


def create_semester_and_prefix_controls(semesters: list[str], prefix_df: pd.DataFrame) -> tuple:
    """Create interactive controls for semester and prefix selection."""
    # Semester dropdown
    semester_dropdown = alt.binding_select(
        options=['All'] + semesters,
        name='Filter by Semester: '
    )
    semester_select = alt.selection_single(
        fields=['semester'],
        bind=semester_dropdown,
        name='semester',
        init={'semester': 'All'}
    )

    # Prefix dropdown
    prefixes = sorted(set(prefix_df['Course Prefix'].tolist()))
    prefix_dropdown = alt.binding_select(
        options=[None] + prefixes,
        labels=['none'] + prefixes,
        name='Search for a course prefix: '
    )
    prefix_dropdown_select = alt.selection_single(
        fields=['Course Prefix'],
        empty='none',
        bind=prefix_dropdown,
        name='Course Prefix'
    )

    return semester_select, prefix_dropdown_select


def create_prefix_scatter(data_url: str, semester_select, prefix_dropdown_select) -> alt.Chart:
    """Create the prefix scatterplot with interactive selection."""
    prefix_selection = alt.selection_single(fields=['Course Prefix'], empty='none')

    prefix_scatter = (
        alt.Chart(data_url)
        .mark_circle()
        .encode(
            x=alt.X('College:N', title='College'),
            y=alt.Y('Average Grade:Q', title='Average Grade'),
            color=alt.Color('College:N', scale=alt.Scale(scheme='dark2')),
            opacity=alt.condition(prefix_selection | prefix_dropdown_select, alt.value(0.8), alt.value(.2)),
            size=alt.Size('Total Students:Q', scale=alt.Scale(range=[10, 1000])),
            tooltip=['Course Prefix:N', 'Department:N', 'Total Students:Q', 'Average Grade:Q']
        )
        .interactive()
        .add_selection(prefix_selection)
        .add_selection(semester_select)
        .add_selection(prefix_dropdown_select)
        .transform_filter(semester_select)
        .properties(
            width=600,
            title={
                "text": ["1. Choose a Course Prefix"],
                "font": "Trebuchet MS",
                "fontSize": 24,
                "subtitle": ["Average Grade By Course Prefix"],
                "subtitleFont": "Trebuchet MS",
                "subtitleFontSize": 15
            }
        )
    )

    # Outline for selected points
    prefix_scatter_outline = (
        alt.Chart(data_url)
        .mark_point(color='black')
        .encode(
            x=alt.X('College:N', title='College'),
            y=alt.Y('Average Grade:Q', title='Average Grade'),
            opacity=alt.condition(prefix_selection | prefix_dropdown_select, alt.value(1), alt.value(0)),
            size=alt.Size('Total Students:Q', scale=alt.Scale(range=[10, 1000]))
        )
        .properties(width=600)
        .transform_filter(semester_select)
    )

    # Info text about search
    search_infotip_df = pd.DataFrame({'text': ['Scroll to bottom for a dropdown search of prefixes']})
    search_infotip = (
        alt.Chart(search_infotip_df)
        .mark_text(dy=-135, size=12, font='Trebuchet MS')
        .encode(text='text')
    )

    return prefix_scatter + search_infotip + prefix_scatter_outline, prefix_selection


def create_course_scatter(data_url: str, prefix_selection, prefix_dropdown_select, semester_select) -> alt.Chart:
    """Create the course scatterplot filtered by prefix selection."""
    selection_course_name = alt.selection_single(fields=['Course Name'], empty='none')

    # Base canvas so chart is right size before a prefix is selected
    course_scatter_base = (
        alt.Chart({'values': [
            {'avg_gpa': 0, 'Division': 'Graduate'},
            {'avg_gpa': 4, 'Division': 'Upper'},
            {'avg_gpa': 4, 'Division': 'Lower'}
        ]})
        .mark_point(opacity=0)
        .encode(
            y='avg_gpa:Q',
            color=alt.Color('Division:N', scale=alt.Scale(scheme='tableau10'))
        )
    )

    # Main course scatterplot
    course_scatter = (
        alt.Chart(data_url)
        .mark_circle(size=70)
        .encode(
            x=alt.X('Total Students:Q', title='Number of Students', scale=alt.Scale(type='log')),
            y=alt.Y('Average Grade:Q', title='Average Grade'),
            color=alt.Color('Division:N', scale=alt.Scale(scheme='tableau10')),
            opacity=alt.condition(selection_course_name, alt.value(0.8), alt.value(.2)),
            tooltip=['Course Name:N', 'Total Students:Q', 'Average Grade:Q']
        )
        .transform_filter(prefix_dropdown_select | prefix_selection)
        .add_selection(selection_course_name)
        .transform_filter(semester_select)
        .properties(
            title={
                "text": ["2. Choose a Specific Course Within That Prefix"],
                "font": "Trebuchet MS",
                "fontSize": 20,
                "subtitle": ["Grade vs. Number of Students"],
                "subtitleFont": "Trebuchet MS",
                "subtitleFontSize": 15
            }
        )
        .interactive()
    )

    # Outline for selected points
    course_scatter_outline = (
        alt.Chart(data_url)
        .mark_point(color='black', size=70)
        .encode(
            x=alt.X('Total Students:Q', title='Number of Students', scale=alt.Scale(type='log')),
            y=alt.Y('Average Grade:Q', title='Average Grade'),
            opacity=alt.condition(selection_course_name, alt.value(1), alt.value(0))
        )
        .transform_filter(prefix_dropdown_select | prefix_selection)
        .transform_filter(semester_select)
    )

    return course_scatter_base + course_scatter + course_scatter_outline, selection_course_name


def create_grade_bar_chart(
    bar_df_url: str, 
    course_scatter_df: pd.DataFrame,
    prefix_selection, 
    prefix_dropdown_select,
    selection_course_name, 
    semester_select
) -> alt.Chart:
    """Create the grade distribution bar chart for selected course."""

    # Letter grade color mapping
    letter_grade_colors = {
        'A+': '#4caf50', 'A': '#4caf50', 'A-': '#8bc34a',
        'B+': '#cddc39', 'B': '#ffeb3b', 'B-': '#ffc107',
        'C+': '#ffa000', 'C': '#f57c00', 'C-': '#ff5722',
        'D+': '#ff5252', 'D': '#e64a19', 'D-': '#f44336',
        'F': '#d32f2f'
    }

    # Dynamic course name and GPA labels
    unique_course_names = (
        course_scatter_df
        .groupby(['Course Name', 'Course Prefix'])
        .agg(count=('college', 'count'))
        .reset_index()
    )

    course_name_label = (
        alt.Chart(unique_course_names)
        .mark_text(dy=-135, size=18, font='Trebuchet MS')
        .encode(text='Course Name:N')
        .transform_filter(prefix_selection | prefix_dropdown_select)
        .transform_filter(selection_course_name)
    )

    gpa_label = (
        alt.Chart(course_scatter_df)
        .mark_text(dy=-118, size=13, font='Trebuchet MS')
        .encode(text='Average Grade')
        .transform_filter(selection_course_name)
        .transform_filter(prefix_selection | prefix_dropdown_select)
        .transform_filter(semester_select)
    )

    # Base canvas
    bar_base_df = pd.DataFrame({
        'Letter Grade': ['A', 'A-', 'B+', 'B', 'B-', 'C', 'C+', 'C-', 'D', 'D+', 'D-', 'F'],
        'Number Students': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    })
    course_bar_base = (
        alt.Chart(bar_base_df)
        .mark_bar(opacity=0)
        .encode(
            x=alt.X('Letter Grade:O', sort=list(letter_grade_colors.keys())),
            y='Number Students:Q'
        )
    )

    # Bar chart
    course_bar = (
        alt.Chart(bar_df_url)
        .mark_bar()
        .encode(
            x=alt.X('Letter Grade:O', title='Grade Received', sort=list(letter_grade_colors.keys())),
            y=alt.Y('Total Students:Q', title='Number of Students'),
            color=alt.Color('Letter Grade:O', scale=alt.Scale(
                domain=list(letter_grade_colors.keys()),
                range=list(letter_grade_colors.values())
            ), legend=None),
            tooltip=['Total Students:Q', 'Letter Grade:O', 'Grade Points:Q']
        )
        .transform_filter(prefix_selection | prefix_dropdown_select)
        .transform_filter(selection_course_name)
        .transform_filter(semester_select)
        .properties(
            title={
                "text": ["3. View Grade Distribution"],
                "font": "Trebuchet MS",
                "fontSize": 20,
                "subtitle": ["Letter Grade Histogram"],
                "subtitleFont": "Trebuchet MS",
                "subtitleFontSize": 15
            }
        )
    )

    return course_bar_base + course_bar + course_name_label + gpa_label


def create_dashboard(data_dir: Path = Path('data'), output_dir: Path = Path('output')) -> None:
    """
    Create the interactive dashboard and save as HTML.

    Args:
        data_dir: Path to the data directory containing processed CSV files
        output_dir: Path to save the output HTML file
    """
    print("Loading processed data...")
    prefix_scatter_df = pd.read_csv(data_dir / 'processed' / 'prefix_scatter_df.csv')
    course_scatter_df = pd.read_csv(data_dir / 'processed' / 'course_scatter_df.csv')
    bar_df = pd.read_csv(data_dir / 'processed' / 'bar_df.csv')

    # Get list of semesters from prefix scatter data
    semesters = [
        'Fall 2021', 'Summer 2021', 'Spring 2021', 'Fall 2020',
        'Summer 2020', 'Spring 2020', 'Fall 2019', 'Summer 2019',
        'Spring 2019', 'Fall 2018', 'Summer 2018', 'Spring 2018',
        'Fall 2017', 'Summer 2017', 'Spring 2017', 'Fall 2016',
        'Summer 2016', 'Spring 2016', 'Fall 2015', 'Summer 2015',
        'Spring 2015', 'Fall 2014', 'Summer 2014', 'Spring 2014',
        'Fall 2013', 'Summer 2013', 'Spring 2013', 'Fall 2012',
        'Summer 2012', 'Spring 2012', 'Fall 2011', 'Summer 2011'
    ]

    print("Creating interactive controls...")
    semester_select, prefix_dropdown_select = create_semester_and_prefix_controls(semesters, prefix_scatter_df)

    print("Building prefix scatterplot...")
    prefix_scatter_url = 'https://pub-2b49819eca18477991a35a5e2ff85330.r2.dev/prefix_scatter_df.csv'
    course_scatter_url = 'https://pub-2b49819eca18477991a35a5e2ff85330.r2.dev/course_scatter_df.csv'
    bar_df_url = 'https://pub-2b49819eca18477991a35a5e2ff85330.r2.dev/bar_df.csv'

    prefix_scatter_final, prefix_selection = create_prefix_scatter(
        prefix_scatter_url, semester_select, prefix_dropdown_select
    )

    print("Building course scatterplot...")
    course_scatter_final, selection_course_name = create_course_scatter(
        course_scatter_url, prefix_selection, prefix_dropdown_select, semester_select
    )

    print("Building grade distribution bar chart...")
    bar_final = create_grade_bar_chart(
        bar_df_url, course_scatter_df,
        prefix_selection, prefix_dropdown_select,
        selection_course_name, semester_select
    )

    print("Combining visualizations into dashboard...")
    final_viz = (
        (prefix_scatter_final & (course_scatter_final | bar_final).resolve_scale(color='independent'))
    ).resolve_scale(
        color='independent', size='independent'
    ).properties(
        title={
            'text': ['UT Austin Historical Course Grades'],
            'font': 'Trebuchet MS',
            'fontSize': 36,
            'subtitle': ['An exploratory dashboard for course grade distributions', ' '],
            'subtitleFont': 'Trebuchet MS',
            'subtitleFontSize': 18
        }
    )

    output_path = output_dir / 'UT_historical_class_grades.html'
    print(f"\nSaving dashboard to {output_path}...")
    final_viz.save(str(output_path))
    print(f"Dashboard saved successfully!")


if __name__ == '__main__':
    create_dashboard()
