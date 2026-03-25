import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

const LoadingOrb = ({ size = 'large', text = 'Loading...' }) => {
  const orbRef = useRef(null);
  const containerRef = useRef(null);

  const sizeClasses = {
    small: 'w-8 h-8',
    medium: 'w-16 h-16', 
    large: 'w-24 h-24',
    mini: 'w-5 h-5'
  };

  const textSizeClasses = {
    small: 'text-xs',
    medium: 'text-sm',
    large: 'text-base',
    mini: 'text-xs'
  };

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Entrance animation
      gsap.fromTo(orbRef.current,
        { opacity: 0, scale: 0.85, y: 20 },
        { opacity: 1, scale: 1, y: 0, duration: 1, ease: 'power2.out' }
      );

      // Continuous floating animation
      gsap.to(orbRef.current, {
        y: -8,
        duration: 4,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut'
      });

      // Gentle rotation
      gsap.to(orbRef.current, {
        rotation: 360,
        duration: 20,
        repeat: -1,
        ease: 'none'
      });
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className="flex flex-col items-center justify-center">
      <div className={`relative ${sizeClasses[size]}`}>
        <img 
          ref={orbRef}
          src="/orb_glow_sphere.png" 
          alt="Loading Orb" 
          className={`w-full h-full object-contain`}
        />
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
