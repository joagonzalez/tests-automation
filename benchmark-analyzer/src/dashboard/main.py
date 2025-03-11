import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sqlalchemy as sa
from pathlib import Path

def main():
    # Get database path from arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", required=True)
    args, _ = parser.parse_known_args()

    # Connect to database
    engine = sa.create_engine(f"sqlite:///{args.db_path}")

    # Get test results
    query = """
    SELECT tr.timestamp, tr.test_type,
           rt.memory_latency_idle_latency_ns as memory_latency,
           rt.sysbench_cpu_events_per_sec as cpu_performance
    FROM test_runs tr
    JOIN test_results_cpu_memory_benchmark rt ON rt.test_run_id = tr.id
    ORDER BY tr.timestamp
    """

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])  # Convert to datetime

    # Debug information
    st.write("Raw data:")
    st.dataframe(df)  # Show raw data

    # Memory Latency plot
    st.title("Memory Latency")
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['memory_latency'],
            mode='lines+markers',
            name='Memory Latency'
        )
    )
    fig1.update_layout(
        xaxis_title="Time",
        yaxis_title="Latency (ns)"
    )
    st.plotly_chart(fig1)

    # CPU Performance plot
    st.title("CPU Performance")
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['cpu_performance'],
            mode='lines+markers',
            name='Events/sec'
        )
    )
    fig2.update_layout(
        xaxis_title="Time",
        yaxis_title="Events/sec"
    )
    st.plotly_chart(fig2)

if __name__ == "__main__":
    main()