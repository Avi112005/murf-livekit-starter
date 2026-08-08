import { ArrowUpRight, MapPinned, ShieldAlert, Waves } from 'lucide-react';
import { Button } from '@/components/ui/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 mb-4 size-16"
    >
      <path
        d="M15 24V40C15 40.7957 14.6839 41.5587 14.1213 42.1213C13.5587 42.6839 12.7956 43 12 43C11.2044 43 10.4413 42.6839 9.87868 42.1213C9.31607 41.5587 9 40.7957 9 40V24C9 23.2044 9.31607 22.4413 9.87868 21.8787C10.4413 21.3161 11.2044 21 12 21C12.7956 21 13.5587 21.3161 14.1213 21.8787C14.6839 22.4413 15 23.2044 15 24ZM22 5C21.2044 5 20.4413 5.31607 19.8787 5.87868C19.3161 6.44129 19 7.20435 19 8V56C19 56.7957 19.3161 57.5587 19.8787 58.1213C20.4413 58.6839 21.2044 59 22 59C22.7956 59 23.5587 58.6839 24.1213 58.1213C24.6839 57.5587 25 56.7957 25 56V8C25 7.20435 24.6839 6.44129 24.1213 5.87868C23.5587 5.31607 22.7956 5 22 5ZM32 13C31.2044 13 30.4413 13.3161 29.8787 13.8787C29.3161 14.4413 29 15.2044 29 16V48C29 48.7957 29.3161 49.5587 29.8787 50.1213C30.4413 50.6839 31.2044 51 32 51C32.7956 51 33.5587 50.6839 34.1213 50.1213C34.6839 49.5587 35 48.7957 35 48V16C35 15.2044 34.6839 14.4413 34.1213 13.8787C33.5587 13.3161 32.7956 13 32 13ZM42 21C41.2043 21 40.4413 21.3161 39.8787 21.8787C39.3161 22.4413 39 23.2044 39 24V40C39 40.7957 39.3161 41.5587 39.8787 42.1213C40.4413 42.6839 41.2043 43 42 43C42.7957 43 43.5587 42.6839 44.1213 42.1213C44.6839 41.5587 45 40.7957 45 40V24C45 23.2044 44.6839 22.4413 44.1213 21.8787C43.5587 21.3161 42.7957 21 42 21ZM52 17C51.2043 17 50.4413 17.3161 49.8787 17.8787C49.3161 18.4413 49 19.2044 49 20V44C49 44.7957 49.3161 45.5587 49.8787 46.1213C50.4413 46.6839 51.2043 47 52 47C52.7957 47 53.5587 46.6839 54.1213 46.1213C54.6839 45.5587 55 44.7957 55 44V20C55 19.2044 54.6839 18.4413 54.1213 17.8787C53.5587 17.3161 52.7957 17 52 17Z"
        fill="currentColor"
      />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void | Promise<void>;
  errorMessage?: string | null;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  errorMessage,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div
      ref={ref}
      className="relative min-h-svh overflow-hidden bg-[#f5f0e8] text-[#173c39] dark:bg-[#102523] dark:text-[#eff8ed]"
    >
      <div className="pointer-events-none absolute -top-32 right-[-12%] size-[520px] rounded-full bg-[#e6b36b]/25 blur-3xl dark:bg-[#c96b45]/20" />
      <div className="pointer-events-none absolute bottom-[-18%] left-[-10%] size-[420px] rounded-full bg-[#91cdb2]/30 blur-3xl dark:bg-[#277a68]/20" />

      <section className="relative mx-auto flex min-h-svh w-full max-w-6xl flex-col justify-center px-5 py-24 sm:px-8 lg:px-12">
        <div className="mb-12 flex items-center gap-3 text-xs font-bold tracking-[0.24em] text-[#277a68] uppercase dark:text-[#8bd9bb]">
          <span className="size-2 rounded-full bg-[#d66e46] shadow-[0_0_0_5px_rgba(214,110,70,0.15)]" />
          Voice check-in / Disaster response
        </div>

        <div className="grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr] lg:gap-24">
          <div>
            <p className="mb-5 max-w-xl text-sm leading-6 text-[#47716a] dark:text-[#a6c9bd]">
              A calm first conversation for floods, droughts, relief requests, and welfare
              check-ins across India.
            </p>
            <h1 className="max-w-3xl text-5xl leading-[0.98] font-semibold tracking-[-0.06em] text-balance sm:text-7xl">
              When the situation is urgent, start with what matters.
            </h1>
            <p className="mt-7 max-w-xl text-base leading-7 text-[#47716a] dark:text-[#b3d3c8] sm:text-lg">
              Aapda Sahaayak helps you describe what happened, where you are, and who needs
              support. It does not invent alerts or dispatch rescue.
            </p>

            <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
              <Button
                size="lg"
                onClick={onStartCall}
                className="h-14 rounded-full bg-[#173c39] px-7 font-mono text-xs font-bold tracking-[0.12em] text-[#f5f0e8] uppercase shadow-xl shadow-[#173c39]/15 transition-transform hover:-translate-y-0.5 hover:bg-[#285a54] dark:bg-[#eff8ed] dark:text-[#173c39] dark:hover:bg-white"
              >
                {startButtonText}
                <ArrowUpRight className="ml-2 size-4" />
              </Button>
              <span className="text-xs font-medium text-[#6c9288] dark:text-[#9bc0b2]">
                Uses an Indian voice powered by Murf Falcon
              </span>
            </div>

            {errorMessage && (
              <div
                role="alert"
                className="mt-6 flex max-w-xl items-start gap-3 rounded-2xl border border-[#bd5c42]/30 bg-[#fff2ed] p-4 text-sm leading-6 text-[#8d3e2d] dark:bg-[#3b2420] dark:text-[#ffc3ad]"
              >
                <ShieldAlert className="mt-0.5 size-5 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>

          <div className="relative">
            <div className="rounded-[2rem] border border-[#c2d7c9] bg-[#e9f1e8]/80 p-3 shadow-2xl shadow-[#315e54]/10 backdrop-blur dark:border-[#315c54] dark:bg-[#183a35]/80">
              <div className="rounded-[1.5rem] border border-[#cbded1] bg-[#f8fbf6] p-6 dark:border-[#315c54] dark:bg-[#15302d] sm:p-8">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-mono text-[10px] font-bold tracking-[0.2em] text-[#6c9288] uppercase dark:text-[#9bc0b2]">
                      Ready state
                    </p>
                    <p className="mt-2 text-xl font-semibold">Your safety check-in</p>
                  </div>
                  <div className="flex size-12 items-center justify-center rounded-2xl bg-[#f6dfc2] text-[#b8623d] dark:bg-[#4a3228] dark:text-[#f0a27c]">
                    <Waves className="size-6" />
                  </div>
                </div>

                <div className="mt-8 space-y-3">
                  <div className="flex items-center gap-4 rounded-2xl bg-[#edf4ed] p-4 dark:bg-[#1d453e]">
                    <MapPinned className="size-5 text-[#277a68] dark:text-[#8bd9bb]" />
                    <div>
                      <p className="text-sm font-semibold">Where are you?</p>
                      <p className="text-xs text-[#6c9288] dark:text-[#a6c9bd]">Location and access needs</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 rounded-2xl bg-[#edf4ed] p-4 dark:bg-[#1d453e]">
                    <Waves className="size-5 text-[#277a68] dark:text-[#8bd9bb]" />
                    <div>
                      <p className="text-sm font-semibold">What happened?</p>
                      <p className="text-xs text-[#6c9288] dark:text-[#a6c9bd]">Flood, drought, or relief request</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 rounded-2xl bg-[#edf4ed] p-4 dark:bg-[#1d453e]">
                    <ShieldAlert className="size-5 text-[#b8623d] dark:text-[#f0a27c]" />
                    <div>
                      <p className="text-sm font-semibold">Who needs support?</p>
                      <p className="text-xs text-[#6c9288] dark:text-[#a6c9bd]">People affected and urgency</p>
                    </div>
                  </div>
                </div>

                <p className="mt-7 border-t border-[#d5e4d6] pt-5 text-xs leading-5 text-[#6c9288] dark:border-[#315c54] dark:text-[#a6c9bd]">
                  No OTPs. No passwords. No unofficial evacuation orders.
                </p>
              </div>
            </div>
            <div className="absolute -right-4 -bottom-5 -z-10 h-24 w-36 rounded-full bg-[#d66e46]/25 blur-2xl" />
          </div>
        </div>

        <div className="mt-16 flex items-center gap-3 text-xs text-[#6c9288] dark:text-[#9bc0b2]">
          <span className="rounded-full border border-[#c2d7c9] px-3 py-1.5 font-mono text-[10px] tracking-[0.16em] uppercase dark:border-[#315c54]">
            Ready
          </span>
          <span>Tap once, allow your microphone, and speak naturally.</span>
        </div>
      </section>
    </div>
  );
};
