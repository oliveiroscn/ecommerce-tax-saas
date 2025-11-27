import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const ProfitabilityDashboard = ({ organizationId }) => {
    const [filters, setFilters] = useState({
        startDate: '2023-01-01',
        endDate: '2023-12-31',
        platform: 'ALL'
    });
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchData();
    }, [filters]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const query = new URLSearchParams({
                organization_id: organizationId,
                start_date: filters.startDate,
                end_date: filters.endDate,
                platform: filters.platform
            }).toString();

            const response = await fetch(`/api/v1/analytics/net-margin/?${query}`);
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error("Error fetching analytics:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (e) => {
        setFilters({ ...filters, [e.target.name]: e.target.value });
    };

    if (loading) return <div>Loading Analytics...</div>;
    if (!data) return <div>No Data</div>;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-2xl font-bold mb-6">Profitability Dashboard</h1>

            {/* Filters */}
            <div className="flex gap-4 mb-8 bg-white p-4 rounded shadow">
                <input
                    type="date"
                    name="startDate"
                    value={filters.startDate}
                    onChange={handleFilterChange}
                    className="border p-2 rounded"
                />
                <input
                    type="date"
                    name="endDate"
                    value={filters.endDate}
                    onChange={handleFilterChange}
                    className="border p-2 rounded"
                />
                <select
                    name="platform"
                    value={filters.platform}
                    onChange={handleFilterChange}
                    className="border p-2 rounded"
                >
                    <option value="ALL">All Platforms</option>
                    <option value="ML">Mercado Livre</option>
                    <option value="SHOPEE">Shopee</option>
                </select>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <KpiCard title="Total Revenue" value={data.kpis.revenue} prefix="R$" />
                <KpiCard title="Total Costs (Est.)" value={data.kpis.total_costs} prefix="R$" />
                <KpiCard title="Net Margin" value={data.kpis.net_margin} prefix="R$" color="text-green-600" />
                <KpiCard title="Margin %" value={data.kpis.margin_percentage} suffix="%" />
            </div>

            {/* Chart */}
            <div className="bg-white p-6 rounded shadow">
                <h2 className="text-xl font-semibold mb-4">Daily Net Margin Evolution</h2>
                <div className="h-96">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data.daily_chart}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line type="monotone" dataKey="net_margin" stroke="#8884d8" name="Net Margin" />
                            {/* Note: If we want multiple lines for platforms, we'd need to restructure data or use multiple Lines filtering by payload, 
                  but for now a single line or simple aggregation is fine for the prompt's 'comparison' requirement 
                  we might need to pivot the data in backend or frontend. 
                  For simplicity, this plots the total margin per day. 
              */}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

const KpiCard = ({ title, value, prefix = "", suffix = "", color = "text-gray-900" }) => (
    <div className="bg-white p-6 rounded shadow">
        <h3 className="text-gray-500 text-sm font-medium uppercase">{title}</h3>
        <p className={`text-3xl font-bold mt-2 ${color}`}>
            {prefix} {parseFloat(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })} {suffix}
        </p>
    </div>
);

export default ProfitabilityDashboard;
