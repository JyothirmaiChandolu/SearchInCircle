import { useMemo, useRef, useState, type ElementRef } from 'react';
import { FlatList, Modal, Platform, Pressable, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { countryCodes, type CountryItem } from 'react-native-country-codes-picker';
import { CIRCA } from '../lib/theme';

type Props = {
  value: { dialCode: string; flag: string; code: string };
  onChange: (value: { dialCode: string; flag: string; code: string }) => void;
};

/**
 * Tap-to-open country picker. The field itself is a plain, non-editable button —
 * showing the full dial code in a fixed-width box so it never scrolls out of view
 * while the adjacent phone number is being typed. Searching happens in the modal,
 * where there's room to actually see what you're typing.
 */
export function CountryCodeInput({ value, onChange }: Props) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const fieldRef = useRef<ElementRef<typeof View>>(null);

  const sortedCodes = useMemo(
    () => [...countryCodes].sort((a, b) => a.name.en.localeCompare(b.name.en)),
    [],
  );

  const results = useMemo<CountryItem[]>(() => {
    const needle = search.trim().replace(/^\+/, '').toLowerCase();
    if (!needle) return sortedCodes;

    return sortedCodes.filter(
      (item) =>
        item.dial_code.replace('+', '').startsWith(needle) ||
        item.name.en?.toLowerCase().includes(needle),
    );
  }, [search, sortedCodes]);

  const openDropdown = () => {
    setSearch('');
    setOpen(true);
  };

  const handleSelect = (item: CountryItem) => {
    setOpen(false);
    onChange({ dialCode: item.dial_code, flag: item.flag, code: item.code });
  };

  return (
    <View ref={fieldRef} collapsable={false}>
      <Pressable
        onPress={openDropdown}
        accessibilityRole="button"
        accessibilityLabel={`Country code, currently ${value.dialCode}`}
        className="h-14 flex-row items-center gap-1.5 pl-4 pr-2.5"
        style={{ borderRightWidth: 1, borderRightColor: CIRCA.line, width: 104 }}
      >
        <Text className="text-[16px]">{value.flag}</Text>
        <Text
          className="flex-1 text-[15px] font-bold"
          numberOfLines={1}
          style={{ color: CIRCA.ink, fontFamily: 'DMSans_700Bold' }}
        >
          {value.dialCode}
        </Text>
        <Feather name="chevron-down" size={14} color={CIRCA.muted} />
      </Pressable>

      <Modal visible={open} transparent animationType="slide" onRequestClose={() => setOpen(false)}>
        <Pressable
          style={{ flex: 1, backgroundColor: 'rgba(23,23,43,0.4)', justifyContent: 'flex-end' }}
          onPress={() => setOpen(false)}
          accessibilityLabel="Close country list"
        >
          <Pressable onPress={(e) => e.stopPropagation()}>
            <SafeAreaView
              edges={['bottom']}
              style={{
                height: 420,
                backgroundColor: CIRCA.paper,
                borderTopLeftRadius: 20,
                borderTopRightRadius: 20,
                overflow: 'hidden',
                ...Platform.select({
                  web: { boxShadow: '0 -10px 30px -10px rgba(35,42,74,0.3)' },
                  default: {
                    shadowColor: '#232A4A',
                    shadowOpacity: 0.2,
                    shadowRadius: 18,
                    shadowOffset: { width: 0, height: -6 },
                    elevation: 10,
                  },
                }),
              }}
            >
              <View className="flex-row items-center justify-between px-5 pb-3 pt-4">
                <Text className="text-[15px] font-bold" style={{ color: CIRCA.ink, fontFamily: 'Manrope_700Bold' }}>
                  Select country
                </Text>
                <Pressable
                  onPress={() => setOpen(false)}
                  accessibilityRole="button"
                  accessibilityLabel="Close"
                  className="h-8 w-8 items-center justify-center rounded-full"
                  style={{ backgroundColor: CIRCA.soft }}
                >
                  <Feather name="x" size={16} color={CIRCA.ink} />
                </Pressable>
              </View>

              <View className="mx-5 mb-3 h-11 flex-row items-center gap-2 rounded-[12px] px-3" style={{ backgroundColor: CIRCA.soft }}>
                <Feather name="search" size={16} color={CIRCA.muted} />
                <TextInput
                  value={search}
                  onChangeText={setSearch}
                  placeholder="Search country or code"
                  placeholderTextColor="#97A3AD"
                  autoFocus
                  accessibilityLabel="Search country"
                  className="flex-1 text-[14px]"
                  style={{ color: CIRCA.ink }}
                />
              </View>

              <FlatList
                data={results}
                keyExtractor={(item) => item.code}
                keyboardShouldPersistTaps="handled"
                style={{ flex: 1 }}
                ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: CIRCA.line, marginLeft: 52 }} />}
                renderItem={({ item }) => {
                  const selected = item.code === value.code;
                  return (
                    <Pressable
                      onPress={() => handleSelect(item)}
                      className="min-h-[52px] flex-row items-center gap-3 px-5"
                      style={{ backgroundColor: selected ? CIRCA.brandSoft : 'transparent' }}
                      accessibilityRole="button"
                      accessibilityLabel={`${item.name.en}, ${item.dial_code}`}
                    >
                      <Text className="text-[18px]">{item.flag}</Text>
                      <Text className="flex-1 text-[13.5px]" numberOfLines={1} style={{ color: CIRCA.ink, fontFamily: selected ? 'DMSans_600SemiBold' : 'DMSans_400Regular' }}>
                        {item.name.en}
                      </Text>
                      <Text className="text-[13px] font-bold" style={{ color: selected ? CIRCA.brand : CIRCA.muted }}>
                        {item.dial_code}
                      </Text>
                      {selected && <Feather name="check" size={15} color={CIRCA.brand} />}
                    </Pressable>
                  );
                }}
              />
            </SafeAreaView>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}
