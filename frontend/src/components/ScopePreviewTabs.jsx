import React from 'react';

/**
 * Component to render scope section previews
 */
const ScopePreviewTabs = ({ activeTab, parsedDraft }) => {
  if (!parsedDraft) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-12">
        <p>No scope data available. Please finalize the scope first.</p>
      </div>
    );
  }

  // Debug: Log the structure
  console.log('ScopePreviewTabs - activeTab:', activeTab);
  console.log('ScopePreviewTabs - parsedDraft keys:', Object.keys(parsedDraft));
  console.log('ScopePreviewTabs - parsedDraft:', parsedDraft);

  const renderValue = (value, depth = 0) => {
    if (value === null || value === undefined || value === '') return null;

    // Prevent infinite recursion
    if (depth > 5) {
      return <span className="text-gray-500 italic">...</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-gray-500 italic">None</span>;
      return (
        <ul className="list-disc list-inside space-y-1 ml-4">
          {value.map((item, idx) => (
            <li key={idx} className="text-gray-600 dark:text-gray-400">
              {typeof item === 'object' ? renderValue(item, depth + 1) : String(item)}
            </li>
          ))}
        </ul>
      );
    } else if (typeof value === 'object') {
      return (
        <div className="ml-4 mt-2 space-y-2">
          {Object.entries(value).map(([k, v]) => {
            if (v === null || v === undefined || v === '') return null;
            return (
              <div key={k} className="flex gap-2">
                <span className="font-medium text-gray-700 dark:text-gray-300 min-w-[150px]">
                  {k.replace(/_/g, ' ')}:
                </span>
                <div className="flex-1">{renderValue(v, depth + 1)}</div>
              </div>
            );
          })}
        </div>
      );
    } else {
      return <span className="text-gray-600 dark:text-gray-400">{String(value)}</span>;
    }
  };

  const renderSection = (data) => {
    if (!data || typeof data !== 'object') {
      return <div className="text-gray-500 italic">No data available</div>;
    }

    return (
      <div className="space-y-6">
        {Object.entries(data).map(([key, value]) => {
          if (value === null || value === undefined || value === '') return null;

          return (
            <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0">
              <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h4>
              <div className="ml-4">
                {renderValue(value)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const getSectionData = () => {
    // First, try to get section-specific data
    let sectionData = null;

    switch (activeTab) {
      case 'overview':
        sectionData = parsedDraft.overview || parsedDraft.project_overview || parsedDraft.Overview || parsedDraft['Project Overview'];
        break;
      case 'activities':
        sectionData = parsedDraft.activities || parsedDraft.activities_breakdown || parsedDraft['Activities Breakdown'] || parsedDraft.Activities;
        break;
      case 'resourcing':
        sectionData = parsedDraft.resourcing || parsedDraft.resourcing_plan || parsedDraft['Resourcing Plan'] || parsedDraft.Resourcing;
        break;
      case 'architecture':
        sectionData = parsedDraft.architecture || parsedDraft.architecture_diagram || parsedDraft.Architecture || parsedDraft['Architecture Diagram'] || parsedDraft['Architecture diagram'];
        break;
      case 'costing':
        sectionData = parsedDraft.costing || parsedDraft.cost_projection || parsedDraft['Cost Projection'] || parsedDraft.cost_breakdown || parsedDraft.pricing || parsedDraft.Costing;
        break;
      case 'summary':
        sectionData = parsedDraft.summary || parsedDraft.project_summary || parsedDraft.Summary || parsedDraft.Summery || parsedDraft['Project Summary'];
        break;
      default:
        sectionData = null;
    }

    console.log('ScopePreviewTabs - sectionData for', activeTab, ':', sectionData);

    // If no section-specific data, check if parsedDraft itself might be the section
    // (This handles cases where the scope is flat rather than nested)
    if (!sectionData && activeTab === 'overview') {
      // For overview, show the whole parsedDraft if no specific overview section exists
      sectionData = parsedDraft;
    }

    return sectionData;
  };

  const sectionData = getSectionData();

  return (
    <div className="p-6 bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-gray-700 max-h-[600px] overflow-y-auto">
      {sectionData ? renderSection(sectionData) : (
        <div className="text-center text-gray-500 italic py-8">
          <p>This section has no data in the current scope</p>
          <p className="text-sm mt-2">Available fields: {Object.keys(parsedDraft).join(', ')}</p>
        </div>
      )}
    </div>
  );
};

export default ScopePreviewTabs;
