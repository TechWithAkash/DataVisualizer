# app.py
from flask import Flask, render_template, request, jsonify
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import io

app = Flask(__name__)

def process_excel_file(file):
    """Specifically handle Excel files with proper error handling"""
    try:
        # Read all sheets
        xls = pd.ExcelFile(file)
        # If multiple sheets, use the first one
        sheet_name = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)
        return df
    except Exception as e:
        raise Exception(f"Error processing Excel file: {str(e)}")

def create_visualizations(df):
    visualizations = []
    
    # Summary statistics card
    summary_stats = {
        'Total Rows': len(df),
        'Total Columns': len(df.columns),
        'Numeric Columns': len(df.select_dtypes(include=['int64', 'float64']).columns),
        'Text Columns': len(df.select_dtypes(include=['object']).columns),
        'Date Columns': len(df.select_dtypes(include=['datetime64']).columns)
    }
    
    # Create an overview table
    fig_summary = go.Figure(data=[go.Table(
        header=dict(values=['Metric', 'Value'],
                   fill_color='#4361ee',
                   align='left',
                   font=dict(color='white', size=12)),
        cells=dict(values=[list(summary_stats.keys()), list(summary_stats.values())],
                  fill_color='white',
                  align='left'))
    ])
    fig_summary.update_layout(title='Dataset Overview')
    visualizations.append({
        'id': 'summary',
        'plot': json.loads(fig_summary.to_json()),
        'title': 'Dataset Summary'
    })

    # Numeric columns visualization
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    if len(numeric_cols) >= 1:
        # Distribution plots for numeric columns
        fig_dist = make_subplots(rows=1, cols=min(3, len(numeric_cols)),
                               subplot_titles=[f'{col} Distribution' for col in numeric_cols[:3]])
        
        for i, col in enumerate(numeric_cols[:3], 1):
            fig_dist.add_trace(
                go.Histogram(x=df[col], name=col, nbinsx=30,
                            marker_color='#4361ee'),
                row=1, col=i
            )
        
        fig_dist.update_layout(title='Numerical Data Distribution',
                             showlegend=False,
                             height=400)
        visualizations.append({
            'id': 'distribution',
            'plot': json.loads(fig_dist.to_json()),
            'title': 'Data Distribution'
        })

        # Correlation heatmap for numeric columns
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            fig_corr = px.imshow(corr_matrix,
                               color_continuous_scale='RdBu',
                               title='Correlation Matrix')
            visualizations.append({
                'id': 'correlation',
                'plot': json.loads(fig_corr.to_json()),
                'title': 'Correlation Analysis'
            })

    # Time series if date column exists
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) > 0 and len(numeric_cols) > 0:
        fig_time = go.Figure()
        for num_col in numeric_cols[:3]:  # Show up to 3 numeric columns
            fig_time.add_trace(
                go.Scatter(x=df[date_cols[0]], y=df[num_col],
                          name=num_col, mode='lines+markers')
            )
        fig_time.update_layout(title='Time Series Analysis',
                             xaxis_title=date_cols[0],
                             yaxis_title='Value',
                             hovermode='x unified')
        visualizations.append({
            'id': 'timeseries',
            'plot': json.loads(fig_time.to_json()),
            'title': 'Time Series Analysis'
        })

    # Categorical data visualization
    cat_cols = df.select_dtypes(include=['object']).columns
    if len(cat_cols) > 0 and len(numeric_cols) > 0:
        # Create bar charts for categorical vs numeric
        fig_cat = px.bar(df, x=cat_cols[0], y=numeric_cols[0],
                        title=f'{cat_cols[0]} vs {numeric_cols[0]}',
                        color_discrete_sequence=['#4361ee'])
        visualizations.append({
            'id': 'categorical',
            'plot': json.loads(fig_cat.to_json()),
            'title': 'Categorical Analysis'
        })

    return visualizations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.stream.read().decode("UTF8")))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = process_excel_file(file)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        # Generate visualizations
        visualizations = create_visualizations(df)
        
        return jsonify({
            'message': 'File processed successfully',
            'visualizations': visualizations,
            'filename': file.filename
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)