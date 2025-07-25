import React, { useEffect, useRef } from 'react';

// Simple chart component - in production, you'd use a library like Chart.js, D3, or Recharts
const Chart = ({
    data = [],
    type = 'line',
    height = 300,
    width = '100%',
    color = '#2563eb',
    backgroundColor = 'transparent'
}) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);

    useEffect(() => {
        if (!data.length || !canvasRef.current) return;

        drawChart();
    }, [data, type, height, width]);

    const drawChart = () => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const container = containerRef.current;

        // Set canvas size
        canvas.width = container.offsetWidth;
        canvas.height = height;

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!data.length) {
            drawNoDataMessage(ctx, canvas);
            return;
        }

        // Calculate dimensions
        const padding = 40;
        const chartWidth = canvas.width - 2 * padding;
        const chartHeight = canvas.height - 2 * padding;

        // Prepare data based on chart type
        let processedData = processData(data);

        // Draw chart based on type
        switch (type) {
            case 'line':
                drawLineChart(ctx, processedData, padding, chartWidth, chartHeight);
                break;
            case 'area':
                drawAreaChart(ctx, processedData, padding, chartWidth, chartHeight);
                break;
            case 'bar':
                drawBarChart(ctx, processedData, padding, chartWidth, chartHeight);
                break;
            case 'pie':
                drawPieChart(ctx, processedData, canvas.width / 2, canvas.height / 2, Math.min(chartWidth, chartHeight) / 3);
                break;
            default:
                drawLineChart(ctx, processedData, padding, chartWidth, chartHeight);
        }
    };

    const processData = (data) => {
        if (type === 'pie') {
            return data.map(item => ({
                label: item.name || item.label,
                value: item.value || item.y
            }));
        }

        return data.map((item, index) => ({
            x: item.x || item.date || index,
            y: item.y || item.value || 0,
            label: item.label || item.name
        }));
    };

    const drawNoDataMessage = (ctx, canvas) => {
        ctx.fillStyle = '#64748b';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
    };

    const drawLineChart = (ctx, data, padding, chartWidth, chartHeight) => {
        if (!data.length) return;

        // Calculate min/max values
        const values = data.map(d => d.y);
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue || 1;

        // Draw grid lines
        drawGrid(ctx, padding, chartWidth, chartHeight, '#e5e7eb');

        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        data.forEach((point, index) => {
            const x = padding + (index / (data.length - 1)) * chartWidth;
            const y = padding + chartHeight - ((point.y - minValue) / valueRange) * chartHeight;

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Draw points
        data.forEach((point, index) => {
            const x = padding + (index / (data.length - 1)) * chartWidth;
            const y = padding + chartHeight - ((point.y - minValue) / valueRange) * chartHeight;

            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
        });
    };

    const drawAreaChart = (ctx, data, padding, chartWidth, chartHeight) => {
        if (!data.length) return;

        const values = data.map(d => d.y);
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue || 1;

        // Draw grid
        drawGrid(ctx, padding, chartWidth, chartHeight, '#e5e7eb');

        // Create gradient
        const gradient = ctx.createLinearGradient(0, padding, 0, padding + chartHeight);
        gradient.addColorStop(0, color + '40'); // 25% opacity
        gradient.addColorStop(1, color + '10'); // 6% opacity

        // Draw area
        ctx.beginPath();
        ctx.fillStyle = gradient;

        data.forEach((point, index) => {
            const x = padding + (index / (data.length - 1)) * chartWidth;
            const y = padding + chartHeight - ((point.y - minValue) / valueRange) * chartHeight;

            if (index === 0) {
                ctx.moveTo(x, padding + chartHeight);
                ctx.lineTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.lineTo(padding + chartWidth, padding + chartHeight);
        ctx.closePath();
        ctx.fill();

        // Draw line on top
        drawLineChart(ctx, data, padding, chartWidth, chartHeight);
    };

    const drawBarChart = (ctx, data, padding, chartWidth, chartHeight) => {
        if (!data.length) return;

        const values = data.map(d => d.y);
        const minValue = Math.min(0, Math.min(...values));
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue || 1;

        // Draw grid
        drawGrid(ctx, padding, chartWidth, chartHeight, '#e5e7eb');

        const barWidth = chartWidth / data.length * 0.8;
        const barSpacing = chartWidth / data.length * 0.2;

        data.forEach((point, index) => {
            const x = padding + index * (chartWidth / data.length) + barSpacing / 2;
            const barHeight = Math.abs(point.y - minValue) / valueRange * chartHeight;
            const y = point.y >= 0
                ? padding + chartHeight - barHeight
                : padding + chartHeight - (Math.abs(minValue) / valueRange) * chartHeight;

            ctx.fillStyle = point.y >= 0 ? color : '#ef4444';
            ctx.fillRect(x, y, barWidth, barHeight);
        });
    };

    const drawPieChart = (ctx, data, centerX, centerY, radius) => {
        if (!data.length) return;

        const total = data.reduce((sum, item) => sum + item.value, 0);
        let startAngle = -Math.PI / 2;

        const colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'
        ];

        data.forEach((item, index) => {
            const sliceAngle = (item.value / total) * 2 * Math.PI;

            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
            ctx.closePath();

            ctx.fillStyle = colors[index % colors.length];
            ctx.fill();

            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Draw label
            const labelAngle = startAngle + sliceAngle / 2;
            const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
            const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);

            ctx.fillStyle = '#ffffff';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(`${((item.value / total) * 100).toFixed(1)}%`, labelX, labelY);

            startAngle += sliceAngle;
        });
    };

    const drawGrid = (ctx, padding, chartWidth, chartHeight, color) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;

        // Horizontal lines
        for (let i = 0; i <= 5; i++) {
            const y = padding + (i / 5) * chartHeight;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(padding + chartWidth, y);
            ctx.stroke();
        }

        // Vertical lines
        for (let i = 0; i <= 5; i++) {
            const x = padding + (i / 5) * chartWidth;
            ctx.beginPath();
            ctx.moveTo(x, padding);
            ctx.lineTo(x, padding + chartHeight);
            ctx.stroke();
        }
    };

    return (
        <div
            ref={containerRef}
            className="chart-container"
            style={{ width, height, position: 'relative' }}
        >
            <canvas
                ref={canvasRef}
                style={{
                    width: '100%',
                    height: '100%',
                    backgroundColor
                }}
            />
            {data.length === 0 && (
                <div className="chart-no-data">
                    <p>No data available</p>
                </div>
            )}
        </div>
    );
};

export default Chart; 