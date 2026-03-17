import React from 'react';

const LoadingOrb = ({ size = 'large', text = 'Loading...' }) => {
  const sizeClasses = {
    small: 'w-8 h-8',
    medium: 'w-16 h-16', 
    large: 'w-24 h-24',
    mini: 'w-5 h-5'
  };

  const particleSizes = {
    small: 'w-1 h-1',
    medium: 'w-1.5 h-1.5',
    large: 'w-2 h-2',
    mini: 'w-1 h-1'
  };

  const textSizeClasses = {
    small: 'text-xs',
    medium: 'text-sm',
    large: 'text-base',
    mini: 'text-xs'
  };

  return (
    <div className="flex flex-col items-center justify-center">
      <div className={`relative ${sizeClasses[size]}`}>
        {/* Outer glow */}
        <div className="absolute inset-0 rounded-full bg-violet-500/20 blur-xl animate-pulse"></div>
        
        {/* Middle ring */}
        <div className="absolute inset-2 rounded-full border-2 border-violet-500/30 animate-spin"></div>
        
        {/* Inner core */}
        <div className="absolute inset-4 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg">
          <div className="absolute inset-0 rounded-full bg-white/20 blur-sm"></div>
        </div>
        
        {/* Orbiting particles */}
        <div className="absolute inset-0 rounded-full">
          <div className={`absolute top-0 left-1/2 ${particleSizes[size]} bg-violet-400 rounded-full -translate-x-1/2 -translate-y-1/2 animate-pulse`}></div>
          <div className={`absolute bottom-0 left-1/2 ${particleSizes[size]} bg-purple-400 rounded-full -translate-x-1/2 translate-y-1/2 animate-pulse`} style={{animationDelay: '0.5s'}}></div>
          <div className={`absolute left-0 top-1/2 ${particleSizes[size]} bg-indigo-400 rounded-full -translate-y-1/2 -translate-x-1/2 animate-pulse`} style={{animationDelay: '1s'}}></div>
          <div className={`absolute right-0 top-1/2 ${particleSizes[size]} bg-blue-400 rounded-full -translate-y-1/2 translate-x-1/2 animate-pulse`} style={{animationDelay: '1.5s'}}></div>
        </div>
        
        {/* Pulsing waves */}
        <div className="absolute inset-0 rounded-full border border-violet-500/20 animate-ping"></div>
        <div className="absolute inset-0 rounded-full border border-violet-500/10 animate-ping" style={{animationDelay: '1s'}}></div>
      </div>
      
      {text && (
        <p className={`text-gray-400 mt-6 text-center animate-pulse ${textSizeClasses[size]}`}>
          {text}
        </p>
      )}
    </div>
  );
};

export default LoadingOrb;
