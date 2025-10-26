"""Data preparation module for UT Austin grade distribution data."""
import os
import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def load_and_engineer_data(data_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    """Load raw data and perform all feature engineering."""
    
    # Read in raw data and prefix to college mapping
    df = pd.read_csv(os.path.join(data_dir, 'raw', 'all_years_grade_distribution.csv'))
    prefix_to_college = pd.read_csv(os.path.join(data_dir, 'raw', 'prefix_to_college.csv'))

    # Create prefix to college dictionary and map
    prefix_to_college_dict = dict(zip(
        prefix_to_college['COURSE_CODE'].tolist(),
        prefix_to_college['COLLEGE'].tolist()
    ))

    all_colleges = set(prefix_to_college_dict.values())

    grade_to_gpa = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.67,
        'B+': 3.33, 'B': 3.0, 'B-': 2.67,
        'C+': 2.33, 'C': 2, 'C-': 1.67,
        'D+': 1.33, 'D': 1, 'D-': 0.67,
        'F': 0, 'Other': np.nan
    }

    null_dept_mapping = {
        'UDN': 'Urban Design',
        'ECE': 'Electrical Engineering'
    }

    df = df.assign(
        college = lambda df_: df_['course_prefix'].replace(prefix_to_college_dict),
        num_students = lambda df_: df_['num_students'].astype(str).str.replace(',', '').astype(float),
        section_number = lambda df_: df_['course_full_name'].str.split('no.').str[-1],
        letter_grade = lambda df_: df_['letter_grade'].replace({'A+': 'A'}),
        gpa = lambda df_: df_['letter_grade'].replace(grade_to_gpa),
        semester_name = lambda df_: df_['semester'].str.split(' ').str[0],
        semester_year = lambda df_: df_['semester'].str.split(' ').str[1].astype(int),
        course_display_name = lambda df_: df_['course_prefix'] + ' ' + df_['course_number'],
        gpa_sum = lambda df_: df_['gpa'] * df_['num_students'],
        course_number_int = lambda df_: df_['course_number'].str.replace(r'\D', '', regex=True).str[1:].astype(int),
        Division = lambda df_: np.select(
            condlist=[df_['course_number_int'] > 79, df_['course_number_int'] > 19],
            choicelist=['Graduate', 'Upper'],
            default='Lower'
        ),
        department = lambda df_: df_.apply(
            lambda row: row['department'] if row['department'] != '' else
            null_dept_mapping.get(row['course_prefix'], ''), axis=1
        ),
        month_and_day = lambda df_: np.select(
            condlist=[df_['semester_name']=='Fall', df_['semester_name']=='Spring', df_['semester_name']=='Summer'],
            choicelist=['-08-25', '-01-20', '-06-01'],
            default='ERROR'
        ),
        date = lambda df_: pd.to_datetime(df_['semester_year'].astype(str) + df_['month_and_day'])
    ).assign(
        college = lambda df_: np.where(df_['college'].isin(all_colleges), df_['college'], 'Other')
    )

    semesters = df.sort_values('date')['semester'].unique().tolist()

    return df, semesters


def create_prefix_scatter_df(df: pd.DataFrame, semesters: list[str]) -> pd.DataFrame:
    """Create aggregated dataframe for prefix scatterplot."""
    # Create an aggregated DF across all semesters
    prefix_scatter_df = (
        df
        .groupby(['college', 'course_prefix', 'department'])
        .agg(total_students=('num_students', 'sum'), gpa_total=('gpa_sum', 'sum'))
        .reset_index()
        .assign(
            avg_gpa=lambda x: x['gpa_total'] / x['total_students'],
            semester='All'
        )
    )

    # Create the same DF for each semester
    semester_dfs = [
        (
            df
            .query("semester == @semester")
            .groupby(['college', 'course_prefix', 'department'])
            .agg(total_students=('num_students', 'sum'), gpa_total=('gpa_sum', 'sum'))
            .reset_index()
            .assign(
                avg_gpa=lambda x: x['gpa_total'] / x['total_students'],
                semester=semester
            )
        )
        for semester in semesters
    ]

    prefix_scatter_df = (
        pd.concat([prefix_scatter_df] + semester_dfs)
        .rename(columns={
            'course_prefix': 'Course Prefix',
            'department': 'Department',
            'total_students': 'Total Students',
            'avg_gpa': 'Average Grade',
            'college': 'College'
        })
        .assign(**{'Average Grade': lambda x: x['Average Grade'].round(4)})
    )

    return prefix_scatter_df


def create_course_scatter_df(df: pd.DataFrame, semesters: list[str]) -> pd.DataFrame:
    """Create aggregated dataframe for course scatterplot."""
    # Create an aggregated DF across all semesters
    course_scatter_df = (
        df
        .groupby(['college', 'course_prefix', 'course_number', 'department', 'course_display_name', 'Division'])
        .agg(total_students=('num_students', 'sum'), gpa_total=('gpa_sum', 'sum'))
        .reset_index()
        .assign(
            avg_gpa=lambda x: x['gpa_total'] / x['total_students'],
            semester='All'
        )
    )

    # Create the same DF for each semester
    semester_dfs = [
        (
            df
            .query("semester == @semester")
            .groupby(['college', 'course_prefix', 'course_number', 'department', 'course_display_name', 'Division'])
            .agg(total_students=('num_students', 'sum'), gpa_total=('gpa_sum', 'sum'))
            .reset_index()
            .assign(
                avg_gpa=lambda x: x['gpa_total'] / x['total_students'],
                semester=semester
            )
        )
        for semester in semesters
    ]

    course_scatter_df = (
        pd.concat([course_scatter_df] + semester_dfs)
        .rename(columns={
            'course_prefix': 'Course Prefix',
            'department': 'Department',
            'total_students': 'Total Students',
            'avg_gpa': 'Average Grade',
            'course_display_name': 'Course Name'
        })
        .assign(**{'Average Grade': lambda x: x['Average Grade'].round(4)})
    )

    return course_scatter_df


def create_bar_df(df: pd.DataFrame, semesters: list[str]) -> pd.DataFrame:
    """Create aggregated dataframe for grade distribution bar chart."""
    # Create an aggregated DF across all semesters
    bar_df = (
        df
        .groupby(['college', 'course_prefix', 'course_number', 'department', 'letter_grade', 'gpa', 'course_display_name'])
        .agg(total_students=('num_students', 'sum'))
        .reset_index()
        .assign(semester='All')
    )

    # Create the same DF for each semester
    semester_dfs = [
        (
            df
            .query("semester == @semester")
            .groupby(['college', 'course_prefix', 'course_number', 'department', 'letter_grade', 'gpa', 'course_display_name'])
            .agg(total_students=('num_students', 'sum'))
            .reset_index()
            .assign(semester=semester)
        )
        for semester in semesters
    ]

    bar_df = (
        pd.concat([bar_df] + semester_dfs)
        .rename(columns={
            'course_prefix': 'Course Prefix',
            'department': 'Department',
            'total_students': 'Total Students',
            'gpa': 'Grade Points',
            'course_display_name': 'Course Name',
            'letter_grade': 'Letter Grade'
        })
    )

    return bar_df


def prepare_data(data_dir: Path = Path('data')) -> None:
    """
    Main data preparation pipeline that loads, engineers, and saves all processed datasets.

    Args:
        data_dir: Path to the data directory containing raw/ and processed/ subdirectories
    """
    print("Loading and engineering data...")
    df, semesters = load_and_engineer_data(data_dir)
    print(f"Loaded {len(df):,} rows of grade data across {len(semesters)} semesters")

    print("\nCreating prefix scatter dataset...")
    prefix_scatter_df = create_prefix_scatter_df(df, semesters)
    output_path = data_dir / 'processed' / 'prefix_scatter_df.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prefix_scatter_df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

    print("\nCreating course scatter dataset...")
    course_scatter_df = create_course_scatter_df(df, semesters)
    output_path = data_dir / 'processed' / 'course_scatter_df.csv'
    course_scatter_df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

    print("\nCreating bar chart dataset...")
    bar_df = create_bar_df(df, semesters)
    output_path = data_dir / 'processed' / 'bar_df.csv'
    bar_df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

    print("\nData preparation complete!")


if __name__ == '__main__':
    prepare_data()
