import React, { useState } from 'react';

const TaxSimulationPanel = ({ transactionIds }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [regime, setRegime] = useState('SIMPLES');
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);

    const runSimulation = async () => {
        if (!transactionIds || transactionIds.length === 0) {
            alert("No transactions selected");
            return;
        }
        setLoading(true);
        try {
            const response = await fetch('/api/v1/analytics/simulate-tax/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transaction_ids: transactionIds,
                    simulated_regime: regime
                })
            });
            const data = await response.json();
            setResults(data);
        } catch (error) {
            console.error("Simulation error:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed bottom-4 right-4 z-50">
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded shadow-lg hover:bg-blue-700"
                >
                    Simulate Tax Scenario
                </button>
            )}

            {isOpen && (
                <div className="bg-white p-6 rounded shadow-2xl border w-96 max-h-[80vh] overflow-auto">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="font-bold text-lg">Tax Simulation</h3>
                        <button onClick={() => setIsOpen(false)} className="text-gray-500">X</button>
                    </div>

                    <div className="mb-4">
                        <label className="block text-sm font-medium mb-1">Select Regime</label>
                        <select
                            value={regime}
                            onChange={(e) => setRegime(e.target.value)}
                            className="w-full border p-2 rounded"
                        >
                            <option value="SIMPLES">Simples Nacional (6%)</option>
                            <option value="PADRAO">Regime Padrão (27.25%)</option>
                            <option value="EFETIVA_1">Carga Efetiva (10.25%)</option>
                        </select>
                    </div>

                    <button
                        onClick={runSimulation}
                        disabled={loading}
                        className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 mb-4"
                    >
                        {loading ? 'Simulating...' : 'Run Simulation'}
                    </button>

                    {results && (
                        <div className="space-y-2">
                            <h4 className="font-semibold text-sm">Results ({results.length} items)</h4>
                            <div className="text-xs text-gray-600">
                                Comparing Current vs {regime}
                            </div>
                            <div className="max-h-60 overflow-y-auto">
                                <table className="w-full text-xs text-left">
                                    <thead>
                                        <tr className="border-b">
                                            <th className="py-1">ID</th>
                                            <th className="py-1">Current</th>
                                            <th className="py-1">Simulated</th>
                                            <th className="py-1">Diff</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {results.map((res) => (
                                            <tr key={res.transaction_id} className="border-b">
                                                <td className="py-1">{res.external_id}</td>
                                                <td className="py-1">R$ {parseFloat(res.current_margin).toFixed(2)}</td>
                                                <td className="py-1">R$ {parseFloat(res.simulated_margin).toFixed(2)}</td>
                                                <td className={`py-1 font-bold ${res.diff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                    {res.diff >= 0 ? '+' : ''}{parseFloat(res.diff).toFixed(2)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default TaxSimulationPanel;
