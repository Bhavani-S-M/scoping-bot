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

  const renderValue = (value) => {
    if (value === null || value === undefined) return null;

    if (Array.isArray(value)) {
      return (
        <ul className="list-disc list-inside space-y-1 ml-4">
          {value.map((item, idx) => (
            <li key={idx} className="text-gray-600 dark:text-gray-400">
              {typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item)}
            </li>
          ))}
        </ul>
      );
    } else if (typeof value === 'object') {
      return (
        <div className="ml-4 mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="mb-2">
              <span className="font-medium text-gray-700 dark:text-gray-300">{k.replace(/_/g, ' ')}: </span>
              {renderValue(v)}
            </div>
          ))}
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
      <div className="space-y-4">
        {Object.entries(data).map(([key, value]) => {
          if (value === null || value === undefined) return null;

          return (
            <div key={key} className="mb-4">
              <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">
                {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h4>
              {renderValue(value)}
            </div>
          );
        })}
      </div>
    );
  };

  const getSectionData = () => {
    switch (activeTab) {
      case 'overview':
        return parsedDraft.overview || parsedDraft.project_overview;
      case 'architecture':
        return parsedDraft.architecture || parsedDraft.architecture_diagram;
      case 'solution':
        return parsedDraft.solution_components || parsedDraft.solution || parsedDraft.technical_solution;
      case 'assumptions':
        return parsedDraft.assumptions || parsedDraft.key_assumptions;
      case 'timeline':
        return parsedDraft.timeline || parsedDraft.project_timeline || parsedDraft.delivery_timeline;
      case 'costing':
        return parsedDraft.costing || parsedDraft.cost_breakdown || parsedDraft.pricing;
      default:
        return null;
    }
  };

  const sectionData = getSectionData();

  return (
    <div className="p-6 bg-white dark:bg-dark-card rounded-lg border border-gray-200 dark:border-gray-700 max-h-[600px] overflow-y-auto">
      {sectionData ? renderSection(sectionData) : (
        <div className="text-center text-gray-500 italic py-8">
          This section has no data in the current scope
        </div>
      )}
    </div>
  );
};

export default ScopePreviewTabs;
