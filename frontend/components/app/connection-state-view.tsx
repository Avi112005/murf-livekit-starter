import { LoaderCircle, Mic, Radio, RotateCcw, ShieldAlert, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ConnectionStateViewProps {
  state: 'connecting' | 'ended';
  onStartCall: () => void | Promise<void>;
  errorMessage?: string | null;
}

export function ConnectionStateView({
  state,
  onStartCall,
  errorMessage,
}: ConnectionStateViewProps) {
  const isConnecting = state === 'connecting';

  return (
    <div className="relative flex min-h-svh items-center justify-center overflow-hidden bg-[#f5f0e8] px-5 text-[#173c39] dark:bg-[#102523] dark:text-[#eff8ed]">
      <div className="pointer-events-none absolute top-1/4 left-1/2 size-[420px] -translate-x-1/2 rounded-full bg-[#91cdb2]/20 blur-3xl dark:bg-[#277a68]/20" />
      <div className="relative w-full max-w-xl text-center">
        <div className="mx-auto flex size-20 items-center justify-center rounded-[1.75rem] border border-[#c2d7c9] bg-[#e9f1e8] text-[#277a68] shadow-xl shadow-[#315e54]/10 dark:border-[#315c54] dark:bg-[#183a35] dark:text-[#8bd9bb]">
          {isConnecting ? (
            <LoaderCircle className="size-9 animate-spin" />
          ) : errorMessage ? (
            <WifiOff className="size-9 text-[#b8623d]" />
          ) : (
            <Radio className="size-9" />
          )}
        </div>
        <p className="mt-8 font-mono text-[10px] font-bold tracking-[0.24em] text-[#b8623d] uppercase dark:text-[#f0a27c]">
          {isConnecting ? 'Connecting' : errorMessage ? 'Connection issue' : 'Call ended'}
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-5xl">
          {isConnecting ? 'Joining your safety check-in' : errorMessage ? 'Let’s try that again' : 'Your check-in is complete'}
        </h1>
        <p className="mx-auto mt-5 max-w-md text-base leading-7 text-[#5d8178] dark:text-[#a6c9bd]">
          {isConnecting
            ? 'Please wait while Aapda Sahaayak joins the secure voice room.'
            : errorMessage ?? 'You can start another conversation whenever you are ready.'}
        </p>

        {errorMessage && (
          <div
            role="alert"
            className="mx-auto mt-7 flex max-w-md items-start gap-3 rounded-2xl border border-[#bd5c42]/30 bg-[#fff2ed] p-4 text-left text-sm leading-6 text-[#8d3e2d] dark:bg-[#3b2420] dark:text-[#ffc3ad]"
          >
            <ShieldAlert className="mt-0.5 size-5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {!isConnecting && (
          <Button
            size="lg"
            onClick={onStartCall}
            className="mt-9 h-13 rounded-full bg-[#173c39] px-7 font-mono text-xs font-bold tracking-[0.12em] text-[#f5f0e8] uppercase hover:bg-[#285a54] dark:bg-[#eff8ed] dark:text-[#173c39] dark:hover:bg-white"
          >
            {errorMessage ? <RotateCcw className="mr-2 size-4" /> : <Mic className="mr-2 size-4" />}
            {errorMessage ? 'Try again' : 'Start another check-in'}
          </Button>
        )}
      </div>
    </div>
  );
}
