import { useState } from 'react';
import { Pressable, Text, TextInput, View } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { AURORA } from '../lib/theme';

type Props = {
  label: string;
  placeholder: string;
  values: string[];
  onChange: (values: string[]) => void;
};

/** Free-text chip entry: type, press Add (or Enter), remove with the x. Used for
 * skills/tools/certifications, which are all "a short list of strings" in shape. */
export function ChipInput({ label, placeholder, values, onChange }: Props) {
  const [draft, setDraft] = useState('');

  const add = () => {
    const trimmed = draft.trim();
    if (!trimmed || values.includes(trimmed)) {
      setDraft('');
      return;
    }
    onChange([...values, trimmed]);
    setDraft('');
  };

  const remove = (value: string) => onChange(values.filter((v) => v !== value));

  return (
    <View>
      <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink, fontFamily: 'DMSans_700Bold' }}>
        {label}
      </Text>

      {values.length > 0 && (
        <View className="mb-2 flex-row flex-wrap" style={{ gap: 7 }}>
          {values.map((value) => (
            <View
              key={value}
              className="flex-row items-center rounded-full py-1.5 pl-3 pr-2"
              style={{ backgroundColor: AURORA.avBg }}
            >
              <Text className="text-[12.5px] font-semibold" style={{ color: AURORA.avFg }}>
                {value}
              </Text>
              <Pressable onPress={() => remove(value)} className="ml-1 h-4 w-4 items-center justify-center">
                <Feather name="x" size={12} color={AURORA.avFg} />
              </Pressable>
            </View>
          ))}
        </View>
      )}

      <View className="flex-row items-center rounded-[13px] p-1" style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder={placeholder}
          placeholderTextColor="#97A3AD"
          onSubmitEditing={add}
          className="h-11 flex-1 px-3 text-[13.5px] font-medium"
          style={{ color: AURORA.ink }}
        />
        <Pressable
          onPress={add}
          disabled={!draft.trim()}
          className="h-9 items-center justify-center rounded-[10px] px-3.5"
          style={{ backgroundColor: AURORA.primary, opacity: draft.trim() ? 1 : 0.5 }}
        >
          <Text className="text-[12.5px] font-bold text-white">Add</Text>
        </Pressable>
      </View>
    </View>
  );
}
