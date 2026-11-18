declare module 'react-native-country-codes-picker' {
  import type { ComponentType } from 'react';

  export interface CountryItem {
    name: Record<string, string>;
    dial_code: string;
    code: string;
    flag: string;
  }

  export interface CountryPickerProps {
    show: boolean;
    lang: string;
    popularCountries?: string[];
    excludedCountries?: string[];
    showOnly?: string[];
    inputPlaceholder?: string;
    searchMessage?: string;
    disableBackdrop?: boolean;
    enableModalAvoiding?: boolean;
    onBackdropPress?: () => void;
    onRequestClose?: () => void;
    pickerButtonOnPress: (item: CountryItem) => void;
  }

  export const CountryPicker: ComponentType<CountryPickerProps>;
  export const countryCodes: CountryItem[];
}
