'use client';

import { useEffect, useRef } from 'react';
import { useEliteStore } from '@/lib/store';

interface SoundConfig {
  newSignal: string;
  highConfidence: string;
  trade: string;
  alert: string;
}

// Sound URLs - using Web Audio API compatible tones
const SOUNDS: SoundConfig = {
  newSignal: 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvLZiTcIGWi77eefTQwMUKfj8LZjHAY4kdfyy3ksBSR3x/DdkEAKFF606OuoVRQKRp/g8r5sIQUrhc7y2Yk3CBlou+3nn00MDFCn4/C2YxwGOJHX8st5LAUkd8fw3ZBAC',
  highConfidence: 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvLZiTcIGWi77eefTRAMUKfj8LZjHAY4kdfyy3ksBSR3x/DdkEAKFF606OuoVRQKRp/g8r5sIQUrhc7y2Yk3CBlou+3nn00MDFCn4/C2YxwGOJHX8st5LAUkd8fw3ZBACg==',
  trade: 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvLZiTcIGWi77eefTRAMUKfj8LZjHAY4kdfyy3ksBSR3x/DdkEAKFF606OuoVRQKRp/g8r5sIQUrhc7y2Yk3CBlou+3nn00MDFCn4/C2YxwGOJHX8st5LAUkd8fw3ZBACg==',
  alert: 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvLZiTcIGWi77eefTRAMUKfj8LZjHAY4kdfyy3ksBSR3x/DdkEAKFF606OuoVRQKRp/g8r5sIQUrhc7y2Yk3CBlou+3nn00MDFCn4/C2YxwGOJHX8st5LAUkd8fw3ZBACg==',
};

export function useSoundManager() {
  const audioContextRef = useRef<AudioContext | null>(null);
  const { soundEnabled } = useEliteStore();

  useEffect(() => {
    // Initialize Audio Context
    if (typeof window !== 'undefined') {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    return () => {
      audioContextRef.current?.close();
    };
  }, []);

  const playSound = (type: keyof SoundConfig, volume: number = 0.3) => {
    if (!soundEnabled || !audioContextRef.current) return;

    try {
      const audio = new Audio(SOUNDS[type]);
      audio.volume = volume;
      audio.play().catch(err => console.warn('Audio play failed:', err));
    } catch (error) {
      console.warn('Sound playback error:', error);
    }
  };

  const playBeep = (frequency: number = 800, duration: number = 100, volume: number = 0.3) => {
    if (!soundEnabled || !audioContextRef.current) return;

    try {
      const ctx = audioContextRef.current;
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      oscillator.frequency.value = frequency;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(volume, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration / 1000);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + duration / 1000);
    } catch (error) {
      console.warn('Beep playback error:', error);
    }
  };

  return {
    playSound,
    playBeep,
    playNewSignal: () => playBeep(880, 150, 0.2),
    playHighConfidence: () => {
      playBeep(1046, 100, 0.25);
      setTimeout(() => playBeep(1318, 100, 0.25), 120);
    },
    playTrade: () => {
      playBeep(523, 80, 0.3);
      setTimeout(() => playBeep(659, 80, 0.3), 100);
      setTimeout(() => playBeep(784, 120, 0.3), 200);
    },
    playAlert: () => {
      playBeep(1046, 100, 0.35);
      setTimeout(() => playBeep(784, 100, 0.35), 150);
    },
  };
}
