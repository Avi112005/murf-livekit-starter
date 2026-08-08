'use client';

import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { ConnectionState, Track } from 'livekit-client';
import { useAgent, useSessionContext } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { ConnectionStateView } from '@/components/app/connection-state-view';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

function SessionStatus({ agentState }: { agentState: string }) {
  const status =
    agentState === 'speaking'
      ? {
          label: 'Agent is speaking',
          detail: 'Listen for the next safety step',
          color: 'bg-[#d66e46]',
        }
      : agentState === 'listening'
        ? {
            label: 'Listening to you',
            detail: 'Share what happened in your own words',
            color: 'bg-[#3b9a7d]',
          }
        : {
            label: 'Processing your request',
            detail: 'Organizing the details for your check-in',
            color: 'bg-[#d39b45]',
          };

  return (
    <div
      aria-live="polite"
      className="fixed top-5 left-1/2 z-[70] flex -translate-x-1/2 items-center gap-3 rounded-full border border-[#c2d7c9] bg-[#f8fbf6]/90 px-4 py-2.5 shadow-lg shadow-[#315e54]/10 backdrop-blur dark:border-[#315c54] dark:bg-[#15302d]/90"
    >
      <span className={`size-2 rounded-full ${status.color} shadow-[0_0_0_4px_currentColor]/10`} />
      <span>
        <span className="block text-xs font-bold tracking-wide text-[#173c39] dark:text-[#eff8ed]">
          {status.label}
        </span>
        <span className="hidden text-[10px] text-[#6c9288] sm:block dark:text-[#9bc0b2]">
          {status.detail}
        </span>
      </span>
    </div>
  );
}

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const session = useSessionContext();
  const { isConnected, start } = session;
  const { state: agentState } = useAgent();
  const { resolvedTheme } = useTheme();
  const [hasStarted, setHasStarted] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [microphoneError, setMicrophoneError] = useState<string | null>(null);
  const microphoneTrack = session.local.microphoneTrack;
  const microphoneEnabled = microphoneTrack ? !microphoneTrack.publication.isMuted : false;

  useEffect(() => {
    if (microphoneEnabled) {
      setMicrophoneError(null);
    }
  }, [microphoneEnabled]);

  const handleStartCall = async () => {
    setHasStarted(true);
    setStartError(null);
    setMicrophoneError(null);

    try {
      await start();
    } catch {
      setStartError(
        'We could not start the check-in. Allow microphone access for localhost:3000 in your browser settings, then try again.'
      );
    }
  };

  const handleDeviceError = ({ source }: { source: Track.Source; error: Error }) => {
    if (source === Track.Source.Microphone) {
      setMicrophoneError(
        'Microphone access is blocked. Select the lock icon beside the browser address, allow Microphone, then start the check-in again.'
      );
    }
  };

  const isConnecting = session.connectionState === ConnectionState.Connecting;

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && !hasStarted && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
          errorMessage={startError}
        />
      )}
      {/* Connecting view */}
      {!isConnected && hasStarted && isConnecting && (
        <motion.div key="connecting" {...VIEW_MOTION_PROPS}>
          <ConnectionStateView
            state="connecting"
            onStartCall={handleStartCall}
            errorMessage={startError}
          />
        </motion.div>
      )}
      {/* Ended or failed view */}
      {!isConnected && hasStarted && !isConnecting && (
        <motion.div key="ended" {...VIEW_MOTION_PROPS}>
          <ConnectionStateView
            state="ended"
            onStartCall={handleStartCall}
            errorMessage={startError}
          />
        </motion.div>
      )}
      {/* Session view */}
      {isConnected && (
        <motion.div key="session" {...VIEW_MOTION_PROPS} className="relative min-h-svh">
          <SessionStatus agentState={agentState} />
          {microphoneError && (
            <div
              role="alert"
              className="fixed top-20 left-1/2 z-[70] flex w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 items-center justify-center rounded-2xl border border-[#bd5c42]/30 bg-[#fff2ed]/95 px-4 py-3 text-center text-xs leading-5 text-[#8d3e2d] shadow-lg backdrop-blur dark:bg-[#3b2420]/95 dark:text-[#ffc3ad]"
            >
              {microphoneError}
            </div>
          )}
          <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          onDeviceError={handleDeviceError}
          className="fixed inset-0"
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
