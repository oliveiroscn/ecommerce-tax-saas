import React from 'react';
import ProfitabilityDashboard from '../components/ProfitabilityDashboard';
import TaxSimulationPanel from '../components/TaxSimulationPanel';

// Mock Organization ID for demo purposes. 
// In a real app, this would come from the logged-in user's context or session.
const ORGANIZATION_ID = 1;

// Mock Transaction IDs for simulation.
// Ideally, the Dashboard would allow selecting transactions to pass here.
// For now, we pass an empty list or fetch them in the component.
const MOCK_TRANSACTION_IDS = [1, 2, 3];

const DashboardPage = () => {
    return (
        <div>
            <ProfitabilityDashboard organizationId={ORGANIZATION_ID} />
            <TaxSimulationPanel transactionIds={MOCK_TRANSACTION_IDS} />
        </div>
    );
};

export default DashboardPage;
