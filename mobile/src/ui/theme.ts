export const colors = {
  background: '#F4F5F8',
  surface: '#FFFFFF',
  border: '#DFE2EA',
  text: '#14161C',
  muted: '#646B7C',
  primary: '#4B3FE4',
  primaryPressed: '#3A30C2',
  onPrimary: '#FFFFFF',
  primarySoft: '#E9E7FD',
  danger: '#C4291C',
  dangerSoft: '#FCEBE9',
  success: '#1B7F4B',
  successSoft: '#E4F5EC',
  warning: '#8A5A00',
  warningSoft: '#FFF3D6',
  disabled: '#EDEFF3',
  disabledText: '#A3A9B8',
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };

export const radius = { sm: 8, md: 12, pill: 999 };

export const font = {
  title: { fontSize: 24, fontWeight: '700' as const, color: colors.text },
  heading: { fontSize: 17, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 16, color: colors.text },
  small: { fontSize: 14, color: colors.muted },
};
