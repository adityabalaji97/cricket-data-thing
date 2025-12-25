import React from 'react';
import './wrapped.css';

const WrappedHeader = ({ onMenuClick, onClose }) => {
  return (
    <div className="wrapped-header-row">
      {/* Left side: Logo + Title */}
      <div className="wrapped-header-left">
        <div className="wrapped-logo">
          <span>H</span>
        </div>
        <span className="wrapped-header-title">2025 in hindsight</span>
      </div>
      
      {/* Right side: Menu + Close */}
      <div className="wrapped-header-right">
        {/* Three-dot menu for filters */}
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onMenuClick?.();
          }}
          className="wrapped-header-btn"
          aria-label="Menu"
        >
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="5" r="2"/>
            <circle cx="12" cy="12" r="2"/>
            <circle cx="12" cy="19" r="2"/>
          </svg>
        </button>
        
        {/* Close button */}
        <button 
          onClick={(e) => {
            e.stopPropagation();
            onClose?.();
          }}
          className="wrapped-header-btn"
          aria-label="Close"
        >
          <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default WrappedHeader;
