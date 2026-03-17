import { useEffect } from 'react';

export default function OceanWaves() {
  useEffect(() => {
    // Only add waves if they don't already exist
    if (!document.querySelector('.ocean-waves')) {
      const wavesContainer = document.createElement('div');
      wavesContainer.className = 'ocean-waves';
      
      const bubblesContainer = document.createElement('div');
      bubblesContainer.className = 'bubbles';
      
      // Create 7 bubbles
      for (let i = 1; i <= 7; i++) {
        const bubble = document.createElement('div');
        bubble.className = `bubble`;
        bubblesContainer.appendChild(bubble);
      }
      
      // Find the main container and add waves
      const mainContainer = document.querySelector('.min-h-screen');
      if (mainContainer) {
        mainContainer.appendChild(wavesContainer);
        mainContainer.appendChild(bubblesContainer);
      }
    }
    
    return () => {
      // Cleanup if needed
      const waves = document.querySelector('.ocean-waves');
      const bubbles = document.querySelector('.bubbles');
      if (waves) waves.remove();
      if (bubbles) bubbles.remove();
    };
  }, []);

  return null; // This component doesn't render anything visible
}
