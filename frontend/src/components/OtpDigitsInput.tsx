import { useRef, type ElementRef } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';
import { CIRCA } from '../lib/theme';

type Props = {
  value: string;
  onChange: (value: string) => void;
  length?: number;
};

/** OTP entry with `length` boxes (Cognito uses 6 digits for sign-up confirmation, 8 for sign-in). A single hidden TextInput captures keystrokes; the boxes just render `value`. */
export function OtpDigitsInput({ value, onChange, length = 6 }: Props) {
  const inputRef = useRef<ElementRef<typeof TextInput>>(null);
  const digits = Array.from({ length }, (_, i) => value[i] ?? '');
  const compact = length > 6;
  const gap = compact ? 6 : 8;
  const fontSize = compact ? 16 : 20;

  return (
    <Pressable onPress={() => inputRef.current?.focus()} accessibilityRole="none">
      <View className="flex-row" style={{ gap }}>
        {digits.map((digit, i) => (
          <View
            key={i}
            className="aspect-[0.85] flex-1 items-center justify-center rounded-[13px]"
            style={{
              backgroundColor: CIRCA.soft,
              borderWidth: digit ? 2 : 1,
              borderColor: digit ? CIRCA.brand : CIRCA.line,
              ...(digit
                ? { shadowColor: CIRCA.brand, shadowOpacity: 0.18, shadowRadius: 6, shadowOffset: { width: 0, height: 0 }, elevation: 2 }
                : null),
            }}
          >
            <Text style={{ fontSize, color: CIRCA.ink, fontFamily: 'Manrope_700Bold' }}>{digit}</Text>
          </View>
        ))}
      </View>
      <TextInput
        ref={inputRef}
        value={value}
        onChangeText={(text) => onChange(text.replace(/\D/g, '').slice(0, length))}
        keyboardType="number-pad"
        autoComplete="one-time-code"
        textContentType="oneTimeCode"
        accessibilityLabel="Verification code"
        maxLength={length}
        style={{ position: 'absolute', opacity: 0, height: 1, width: 1 }}
      />
    </Pressable>
  );
}
