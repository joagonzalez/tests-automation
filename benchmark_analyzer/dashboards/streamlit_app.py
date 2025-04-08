# dashboards/streamlit_app.py
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from benchmark_analyzer.db.connector import DatabaseManager
from benchmark_analyzer.db.models import TestRun, Environment, TestType

def load_test_runs(session):
    """Load all test runs with their associated metadata."""
    df = pd.read_sql("""
        SELECT 
            tr.test_run_id,
            tr.created_at,
            tt.test_type,
            e.name as environment,
            tr.engineer,
            tr.comments
        FROM test_runs tr
        JOIN test_types tt ON tr.test_type_id = tt.test_type_id
        JOIN environments e ON tr.environment_id = e.environment_id
        ORDER BY tr.created_at DESC
    """, session.bind)
    
    # Convert created_at to datetime
    df['created_at'] = pd.to_datetime(df['created_at'])
    return df

def load_memory_bandwidth_results(session, test_run_ids=None):
    """Load memory bandwidth test results."""
    query = """
        SELECT 
            r.*,
            tr.created_at as run_date,
            e.name as environment
        FROM results_memory_bandwidth r
        JOIN test_runs tr ON r.test_run_id = tr.test_run_id
        JOIN environments e ON tr.environment_id = e.environment_id
    """
    if test_run_ids and len(test_run_ids) > 0:
        query += f" WHERE r.test_run_id IN ({','.join(map(str, test_run_ids))})"
    
    df = pd.read_sql(query, session.bind)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['run_date'] = pd.to_datetime(df['run_date'])
    return df

def load_cpu_latency_results(session, test_run_ids=None):
    """Load CPU latency test results."""
    query = """
        SELECT 
            r.*,
            tr.created_at as run_date,
            e.name as environment
        FROM results_cpu_latency r
        JOIN test_runs tr ON r.test_run_id = tr.test_run_id
        JOIN environments e ON tr.environment_id = e.environment_id
    """
    if test_run_ids and len(test_run_ids) > 0:
        query += f" WHERE r.test_run_id IN ({','.join(map(str, test_run_ids))})"
    
    df = pd.read_sql(query, session.bind)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['run_date'] = pd.to_datetime(df['run_date'])
    return df

def main():
    st.set_page_config(page_title="Benchmark Results Dashboard", layout="wide")
    st.title("🎯 Benchmark Results Dashboard")

    # Initialize database connection
    db_manager = DatabaseManager()
    
    with db_manager.get_session() as session:
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Load test runs for metadata
        test_runs_df = load_test_runs(session)
        
        if test_runs_df.empty:
            st.warning("No test runs found in the database.")
            return
            
        # Date range filter
        min_date = test_runs_df['created_at'].min().date()
        max_date = test_runs_df['created_at'].max().date()
        
        try:
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        except Exception as e:
            st.error(f"Error setting date range: {str(e)}")
            return

        # Environment filter
        environments = test_runs_df['environment'].unique()
        if len(environments) > 0:
            selected_env = st.sidebar.multiselect(
                "Environment",
                environments,
                default=environments[0]
            )
        else:
            st.warning("No environments found in the database.")
            return

        # Test type selector
        test_type = st.sidebar.selectbox(
            "Test Type",
            ["memory_bandwidth", "cpu_latency"]
        )

        # Filter test runs based on selections
        try:
            filtered_runs = test_runs_df[
                (test_runs_df['created_at'].dt.date >= date_range[0]) &
                (test_runs_df['created_at'].dt.date <= date_range[1]) &
                (test_runs_df['environment'].isin(selected_env)) &
                (test_runs_df['test_type'] == test_type)
            ]
        except Exception as e:
            st.error(f"Error filtering results: {str(e)}")
            return

        if filtered_runs.empty:
            st.warning("No results found for the selected filters.")
            return

        # Display results based on test type
        if test_type == "memory_bandwidth":
            results_df = load_memory_bandwidth_results(session, filtered_runs['test_run_id'].tolist())
            
            if not results_df.empty:
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["📈 Trends", "📊 Comparison", "🔢 Raw Data"])
                
                with tab1:
                    st.subheader("Memory Bandwidth Trends")
                    fig = px.line(results_df, 
                        x='timestamp', 
                        y=['read_bw', 'write_bw'],
                        color='environment',
                        title="Memory Bandwidth Over Time")
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Environment Comparison")
                    fig = px.box(results_df, 
                        x='environment', 
                        y=['read_bw', 'write_bw'],
                        title="Memory Bandwidth Distribution by Environment")
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    st.dataframe(results_df)
            else:
                st.warning("No memory bandwidth results found for the selected filters.")

        else:  # cpu_latency
            results_df = load_cpu_latency_results(session, filtered_runs['test_run_id'].tolist())
            
            if not results_df.empty:
                tab1, tab2, tab3 = st.tabs(["📈 Trends", "📊 Distribution", "🔢 Raw Data"])
                
                with tab1:
                    st.subheader("CPU Latency Trends")
                    fig = px.line(results_df, 
                        x='timestamp', 
                        y='average_ns',
                        color='environment',
                        title="CPU Latency Over Time")
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    st.subheader("Latency Distribution")
                    fig = px.box(results_df, 
                        x='environment', 
                        y='average_ns',
                        title="CPU Latency Distribution by Environment")
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    st.dataframe(results_df)
            else:
                st.warning("No CPU latency results found for the selected filters.")

        # Metadata section
        st.sidebar.markdown("---")
        st.sidebar.subheader("Test Run Metadata")
        st.sidebar.dataframe(
            filtered_runs[['created_at', 'engineer', 'environment', 'comments']]
            .sort_values('created_at', ascending=False)
        )

if __name__ == "__main__":
    main()