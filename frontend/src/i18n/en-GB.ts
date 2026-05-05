import { en_US } from './en-US';

export const en_GB: typeof en_US = {
  ...en_US,
  welcome_subtitle: "Any goal. Any deadline. We'll break it into daily steps, keep you on track, and adapt as you go.",
  // British spelling tweaks
  pricing_sub: 'Cancel anytime. 7-day free trial on Pro & Coach.',
  upgrade_sub: 'Pro from £9/mo · Coach from £21/mo',
  save_amt: 'Save {{amt}}',
};
