import '@remix-run/router';

declare module '@remix-run/router' {
  interface FutureConfig {
    v7_startTransition?: boolean;
    v7_relativeSplatPath?: boolean;
  }
}
