export interface ChartConfig {
  [key: string]: {
    label?: string;
    color?: string;
    theme?: {
      light: string;
      dark: string;
    };
  };
}
