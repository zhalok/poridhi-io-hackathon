#!/usr/bin/env python3
"""
Plot performance results from Locust tests and resource monitoring
"""

import os
import sys
import glob
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import argparse


def plot_response_times(results_dir):
    """Plot response times from Locust CSV files"""
    # Find all locust_stats.csv files
    csv_files = glob.glob(f"{results_dir}/**/locust_stats.csv", recursive=True)
    
    if not csv_files:
        print("No Locust stats files found!")
        return
    
    # Prepare data for plotting
    test_data = []
    
    for csv_file in csv_files:
        test_name = os.path.basename(os.path.dirname(csv_file))
        df = pd.read_csv(csv_file)
        
        # Filter out aggregated stats
        df = df[df['Name'] != 'Aggregated']
        
        for _, row in df.iterrows():
            endpoint = row['Name']
            test_data.append({
                'Test': test_name,
                'Endpoint': endpoint,
                'Median': row['Median Response Time'],
                'P95': row['95%'],
                'P99': row['99%'],
                'RPS': row['Requests/s'],
                'Failures': row['Failure Count']
            })
    
    if not test_data:
        print("No valid data found in Locust stats files!")
        return
    
    # Convert to DataFrame for easier plotting
    stats_df = pd.DataFrame(test_data)
    
    # Plot median response times
    plt.figure(figsize=(12, 8))
    ax = plt.subplot(111)
    
    tests = stats_df['Test'].unique()
    test_order = sorted(tests)  # Sort by test name to maintain order
    
    bar_width = 0.35
    x = np.arange(len(test_order))
    
    endpoints = stats_df['Endpoint'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(endpoints)))
    
    for i, endpoint in enumerate(endpoints):
        endpoint_data = stats_df[stats_df['Endpoint'] == endpoint]
        endpoint_values = []
        
        for test in test_order:
            test_value = endpoint_data[endpoint_data['Test'] == test]['Median'].values
            endpoint_values.append(test_value[0] if len(test_value) > 0 else 0)
        
        ax.bar(x + i * bar_width, endpoint_values, bar_width, label=endpoint, color=colors[i])
    
    ax.set_ylabel('Median Response Time (ms)')
    ax.set_title('Median Response Time by Test and Endpoint')
    ax.set_xticks(x + bar_width * (len(endpoints) - 1) / 2)
    ax.set_xticklabels(test_order, rotation=45, ha='right')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(f"{results_dir}/response_times.png")
    
    # Plot RPS
    plt.figure(figsize=(12, 8))
    ax = plt.subplot(111)
    
    for i, endpoint in enumerate(endpoints):
        endpoint_data = stats_df[stats_df['Endpoint'] == endpoint]
        endpoint_values = []
        
        for test in test_order:
            test_value = endpoint_data[endpoint_data['Test'] == test]['RPS'].values
            endpoint_values.append(test_value[0] if len(test_value) > 0 else 0)
        
        ax.bar(x + i * bar_width, endpoint_values, bar_width, label=endpoint, color=colors[i])
    
    ax.set_ylabel('Requests Per Second')
    ax.set_title('Request Rate by Test and Endpoint')
    ax.set_xticks(x + bar_width * (len(endpoints) - 1) / 2)
    ax.set_xticklabels(test_order, rotation=45, ha='right')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(f"{results_dir}/request_rate.png")
    
    print(f"Response time and request rate plots saved to {results_dir}")


def plot_resource_usage(results_dir):
    """Plot resource usage from monitoring data"""
    # Find all container monitoring files
    resource_files = glob.glob(f"{results_dir}/**/*.csv", recursive=True)
    
    # Filter out locust files
    resource_files = [f for f in resource_files if 'locust' not in f and os.path.basename(f) != 'stats.csv']
    
    if not resource_files:
        print("No resource monitoring files found!")
        return
    
    # Create containers set first
    containers = set()
    for file in resource_files:
        # Extract container name from filename (format: container_name_timestamp.csv)
        try:
            container = os.path.basename(file).split('_')[0]
            if container in ["main-service", "insertion-service", "storage-service", 
                           "sync-consumer-service", "rabbitmq", "qdrant"]:
                containers.add(container)
        except:
            continue
    
    # If no containers found
    if not containers:
        print("No valid container data found in CSV files!")
        # Create empty placeholder image
        plt.figure(figsize=(8, 6))
        plt.text(0.5, 0.5, "No container data available", 
                 horizontalalignment='center', verticalalignment='center')
        plt.savefig(f"{results_dir}/cpu_usage.png")
        plt.savefig(f"{results_dir}/memory_usage.png")
        return
    
    # Plot CPU usage per container
    fig_cpu = plt.figure(figsize=(15, max(10, len(containers) * 2)))
    
    for i, container in enumerate(sorted(containers)):
        container_files = [f for f in resource_files if os.path.basename(f).startswith(container)]
        if not container_files:
            continue
        
        plt.subplot(len(containers), 1, i + 1)
        plot_created = False
        
        for file in container_files:
            try:
                test_name = os.path.basename(os.path.dirname(file))
                df = pd.read_csv(file)
                
                if df.empty:
                    continue
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Check if cpu_percent column exists
                if 'cpu_percent' not in df.columns:
                    continue
                
                plt.plot(df['timestamp'], df['cpu_percent'], label=test_name)
                plot_created = True
            except Exception as e:
                print(f"Error plotting CPU data from {file}: {e}")
                continue
        
        if plot_created:    
            plt.title(f'{container} CPU Usage')
            plt.ylabel('CPU %')
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.gcf().autofmt_xdate()
            plt.grid(True, alpha=0.3)
            
            if i == 0:  # Only show legend for the first plot to save space
                plt.legend()
    
    plt.tight_layout()
    plt.savefig(f"{results_dir}/cpu_usage.png")
    
    # Plot Memory usage per container
    fig_mem = plt.figure(figsize=(15, max(10, len(containers) * 2)))
    
    for i, container in enumerate(sorted(containers)):
        container_files = [f for f in resource_files if os.path.basename(f).startswith(container)]
        if not container_files:
            continue
        
        plt.subplot(len(containers), 1, i + 1)
        plot_created = False
        
        for file in container_files:
            try:
                test_name = os.path.basename(os.path.dirname(file))
                df = pd.read_csv(file)
                
                if df.empty:
                    continue
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Check if memory_percent column exists
                if 'memory_percent' not in df.columns:
                    continue
                
                plt.plot(df['timestamp'], df['memory_percent'], label=test_name)
                plot_created = True
            except Exception as e:
                print(f"Error plotting memory data from {file}: {e}")
                continue
        
        if plot_created:
            plt.title(f'{container} Memory Usage')
            plt.ylabel('Memory %')
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.gcf().autofmt_xdate()
            plt.grid(True, alpha=0.3)
            
            if i == 0:
                plt.legend()
    
    plt.tight_layout()
    plt.savefig(f"{results_dir}/memory_usage.png")
    
    print(f"Resource usage plots saved to {results_dir}")


def generate_performance_report(results_dir):
    """Generate a performance report with key metrics"""
    # Find summary files
    summary_files = glob.glob(f"{results_dir}/**/summary_*.json", recursive=True)
    
    # Find all locust stats files
    csv_files = glob.glob(f"{results_dir}/**/locust_stats.csv", recursive=True)
    
    # Load and process Locust data
    locust_data = {}
    test_durations = {}
    
    for csv_file in csv_files:
        test_name = os.path.basename(os.path.dirname(csv_file))
        
        try:
            df = pd.read_csv(csv_file)
            
            # Get aggregate stats
            agg_row = df[df['Name'] == 'Aggregated']
            if not agg_row.empty:
                locust_data[test_name] = {
                    'total_requests': agg_row['Request Count'].values[0],
                    'failures': agg_row['Failure Count'].values[0],
                    'median_response': agg_row['Median Response Time'].values[0],
                    'p95_response': agg_row['95%'].values[0],
                    'p99_response': agg_row['99%'].values[0],
                    'rps': agg_row['Requests/s'].values[0]
                }
            
            # Try to determine test duration from history file
            history_file = os.path.join(os.path.dirname(csv_file), 'locust_stats_history.csv')
            if os.path.exists(history_file):
                history_df = pd.read_csv(history_file)
                if not history_df.empty:
                    # Calculate duration from timestamp difference
                    try:
                        timestamps = pd.to_datetime(history_df['Timestamp'])
                        duration_seconds = (max(timestamps) - min(timestamps)).total_seconds()
                        test_durations[test_name] = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
                    except:
                        test_durations[test_name] = "N/A"
        except Exception as e:
            print(f"Error processing Locust stats for {test_name}: {e}")
    
    # Check if we have any data
    if not locust_data and not summary_files:
        print("No data found for the performance report!")
        # Create a minimal report
        with open(f"{results_dir}/performance_report.md", 'w') as report:
            report.write("# Performance Test Report\n\n")
            report.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            report.write("No test data was found. Please ensure tests ran successfully.\n")
        return
    
    # Load summaries (if they exist)
    summaries = []
    for file in summary_files:
        with open(file, 'r') as f:
            try:
                data = json.load(f)
                test_dir = os.path.dirname(file)
                data['test_name'] = os.path.basename(test_dir)
                summaries.append(data)
            except json.JSONDecodeError:
                print(f"Error reading summary file: {file}")
    
    # Generate the report
    with open(f"{results_dir}/performance_report.md", 'w') as report:
        report.write("# Performance Test Report\n\n")
        report.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        report.write("## Overview\n\n")
        report.write("This report summarizes the performance tests conducted on the Intent-Based Product Search System.\n\n")
        
        report.write("## Test Summary\n\n")
        report.write("| Test | Duration | Requests | RPS | Failures | Median Response (ms) | P95 Response (ms) |\n")
        report.write("|------|----------|----------|-----|----------|---------------------|-------------------|\n")
        
        for test_name, data in sorted(locust_data.items()):
            duration = test_durations.get(test_name, "N/A")
            report.write(f"| {test_name} | {duration} | {data['total_requests']:.0f} | {data['rps']:.2f} | {data['failures']:.0f} | {data['median_response']:.2f} | {data['p95_response']:.2f} |\n")
        
        if summaries:
            report.write("\n## Resource Usage\n\n")
            report.write("| Test | Container | CPU Max % | CPU Avg % | Memory Max % | Memory Avg % |\n")
            report.write("|------|-----------|-----------|-----------|--------------|-------------|\n")
            
            for summary in sorted(summaries, key=lambda x: x['test_name']):
                for container, metrics in summary['containers'].items():
                    report.write(f"| {summary['test_name']} | {container} | {metrics['cpu_percent']['max']:.2f} | {metrics['cpu_percent']['avg']:.2f} | {metrics['memory_percent']['max']:.2f} | {metrics['memory_percent']['avg']:.2f} |\n")
        elif locust_data:
            report.write("\n## Resource Usage\n\n")
            report.write("Resource usage data was not captured successfully. Please check the monitoring tool configuration.\n")
        
        report.write("\n## Key Findings\n\n")
        
        # Analyze the results to provide insights
        high_latency_tests = {}
        for test, data in locust_data.items():
            if data['p95_response'] > 500:  # Over 0.5 second response time at p95
                high_latency_tests[test] = data['p95_response']
        
        if high_latency_tests:
            report.write("### High Latency Tests\n\n")
            report.write("The following tests showed high latency (P95 > 500ms):\n\n")
            for test, latency in sorted(high_latency_tests.items(), key=lambda x: x[1], reverse=True):
                report.write(f"- {test}: {latency:.2f}ms\n")
            report.write("\n")
        
        # Find high CPU usage from summaries
        high_cpu_containers = []
        for summary in summaries:
            for container, metrics in summary['containers'].items():
                if metrics['cpu_percent']['max'] > 50:  # Over 50% CPU usage
                    high_cpu_containers.append({
                        'test': summary['test_name'],
                        'container': container,
                        'cpu_max': metrics['cpu_percent']['max']
                    })
        
        if high_cpu_containers:
            report.write("### High CPU Usage\n\n")
            report.write("The following tests and containers showed high CPU usage (>50%):\n\n")
            for item in sorted(high_cpu_containers, key=lambda x: x['cpu_max'], reverse=True):
                report.write(f"- {item['test']} - {item['container']}: {item['cpu_max']:.2f}%\n")
            report.write("\n")
        
        report.write("## Recommendations\n\n")
        report.write("Based on the test results, consider the following recommendations:\n\n")
        
        # Generate recommendations based on the findings
        has_recommendations = False
        
        if high_latency_tests:
            has_recommendations = True
            report.write("1. **Optimize Query Performance**: Consider adding caching or optimizing the vector search to reduce high latency.\n")
        
        if high_cpu_containers:
            has_recommendations = True
            container_counts = {}
            for item in high_cpu_containers:
                container_counts[item['container']] = container_counts.get(item['container'], 0) + 1
            
            if container_counts:
                most_stressed = max(container_counts.items(), key=lambda x: x[1])[0]
                report.write(f"2. **Scale {most_stressed}**: This container showed consistent high CPU usage across multiple tests.\n")
        
        if not has_recommendations:
            report.write("- The system handled the load well. No immediate performance optimizations are necessary.\n")
        
        report.write("\n## Conclusion\n\n")
        report.write("The intent-based product search system's performance characteristics have been measured under various load conditions. ")
        report.write("These results provide a baseline for monitoring ongoing performance and for comparison after future optimizations.\n")
    
    print(f"Performance report generated: {results_dir}/performance_report.md")


def main():
    parser = argparse.ArgumentParser(description="Plot performance test results")
    parser.add_argument("results_dir", help="Directory containing test results")
    args = parser.parse_args()
    
    results_dir = args.results_dir
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory '{results_dir}' not found!")
        return 1
    
    print(f"Generating plots for results in: {results_dir}")
    
    # Create plots
    plot_response_times(results_dir)
    plot_resource_usage(results_dir)
    generate_performance_report(results_dir)
    
    print("All plots and reports generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 