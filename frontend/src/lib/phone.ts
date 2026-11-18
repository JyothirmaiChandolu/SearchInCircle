/** Combines a dial code and a locally-entered number into E.164 format Cognito expects. */
export function toE164(dialCode: string, localNumber: string): string {
  const digitsOnly = localNumber.replace(/\D/g, '');
  const code = dialCode.startsWith('+') ? dialCode : `+${dialCode}`;
  return `${code}${digitsOnly}`;
}
