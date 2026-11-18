import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { ChipInput } from './ChipInput';
import { PrimaryButton } from './PrimaryButton';
import { AURORA } from '../lib/theme';
import {
  ApiError,
  createTag,
  deleteTag,
  lookupTaggedPerson,
  suggestSkillsFromResume,
  updateTag,
  type Tag,
  type TaggedPersonPreview,
} from '../lib/api';

type Props = {
  accessToken: string;
  mode: 'create' | 'edit';
  initial?: Tag;
};

export function TagForm({ accessToken, mode, initial }: Props) {
  const isEdit = mode === 'edit';

  const [name, setName] = useState(initial?.person.name ?? '');
  const [phone, setPhone] = useState(initial?.person.phone ?? '');
  const [email, setEmail] = useState(initial?.person.email ?? '');
  const [country, setCountry] = useState(initial?.person.country ?? '');
  const [nickname, setNickname] = useState(initial?.nickname ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [skills, setSkills] = useState<string[]>(initial?.skills ?? []);
  const [tools, setTools] = useState<string[]>(initial?.tools ?? []);
  const [yearsExperience, setYearsExperience] = useState(initial?.yearsExperience?.toString() ?? '');
  const [certifications, setCertifications] = useState<string[]>(initial?.certifications ?? []);
  const [isOpen, setIsOpen] = useState(initial?.isOpen ?? true);

  const [match, setMatch] = useState<TaggedPersonPreview | null>(null);
  const [checkingMatch, setCheckingMatch] = useState(false);
  const [parsingResume, setParsingResume] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dedup check: as soon as a phone/email looks real, see whether this person is
  // already tagged by someone else — before they finish filling out the rest.
  useEffect(() => {
    if (isEdit) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmedPhone = phone.trim();
    const trimmedEmail = email.trim();
    const looksReal = trimmedPhone.length >= 6 || trimmedEmail.includes('@');

    debounceRef.current = setTimeout(
      async () => {
        if (!looksReal) {
          setMatch(null);
          return;
        }
        setCheckingMatch(true);
        try {
          const found = await lookupTaggedPerson(accessToken, {
            phone: trimmedPhone.length >= 6 ? trimmedPhone : undefined,
            email: trimmedEmail.includes('@') ? trimmedEmail : undefined,
          });
          setMatch(found);
        } catch {
          setMatch(null);
        } finally {
          setCheckingMatch(false);
        }
      },
      looksReal ? 500 : 0,
    );

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [phone, email, isEdit, accessToken]);

  const handlePickResume = async () => {
    const result = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'text/plain'] });
    if (result.canceled || !result.assets?.[0]) return;

    const asset = result.assets[0];
    setParsingResume(true);
    setError(null);
    try {
      const found = await suggestSkillsFromResume(accessToken, {
        uri: asset.uri,
        name: asset.name,
        mimeType: asset.mimeType ?? 'application/pdf',
      });
      setTools((prev) => [...new Set([...prev, ...found])]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not read that resume.');
    } finally {
      setParsingResume(false);
    }
  };

  const handleSubmit = async () => {
    if (!isEdit && !name.trim()) {
      setError('Enter their name.');
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      if (isEdit && initial) {
        await updateTag(accessToken, initial.id, {
          nickname: nickname.trim() || undefined,
          description: description.trim() || undefined,
          skills,
          tools,
          yearsExperience: yearsExperience ? Number(yearsExperience) : undefined,
          certifications,
          isOpen,
        });
      } else {
        await createTag(accessToken, {
          personId: match?.id,
          name: name.trim(),
          phone: phone.trim() || undefined,
          email: email.trim() || undefined,
          country: country.trim() || undefined,
          nickname: nickname.trim() || undefined,
          description: description.trim() || undefined,
          skills,
          tools,
          yearsExperience: yearsExperience ? Number(yearsExperience) : undefined,
          certifications,
          isOpen,
        });
      }
      router.back();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save this tag.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!initial) return;
    setSubmitting(true);
    try {
      await deleteTag(accessToken, initial.id);
      router.back();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not remove this tag.');
      setSubmitting(false);
    }
  };

  const inputStyle = {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: AURORA.line,
    color: AURORA.ink,
  };

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: AURORA.bg }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView contentContainerClassName="px-6 pb-10 pt-6" keyboardShouldPersistTaps="handled">
          <View className="flex-row items-center">
            <Pressable
              onPress={() => router.back()}
              className="h-9 w-9 items-center justify-center rounded-full"
              style={{ backgroundColor: '#fff' }}
              accessibilityRole="button"
              accessibilityLabel="Back"
            >
              <Feather name="arrow-left" size={18} color={AURORA.ink} />
            </Pressable>
            <Text className="ml-3 text-[20px] font-bold tracking-tight" style={{ color: AURORA.ink }}>
              {isEdit ? 'Edit tag' : 'Tag someone you know'}
            </Text>
          </View>

          {!isEdit && (
            <>
              <Text className="mb-3 mt-6 text-[13px]" style={{ color: AURORA.ink2 }}>
                Describe someone you personally know — they don&apos;t need an account.
              </Text>

              <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                Name
              </Text>
              <TextInput
                value={name}
                onChangeText={setName}
                placeholder="Their full name"
                placeholderTextColor="#97A3AD"
                className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                style={inputStyle}
              />

              <View className="mt-3 flex-row" style={{ gap: 10 }}>
                <View className="flex-1">
                  <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                    Phone
                  </Text>
                  <TextInput
                    value={phone}
                    onChangeText={setPhone}
                    placeholder="Optional"
                    placeholderTextColor="#97A3AD"
                    keyboardType="phone-pad"
                    className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                    style={inputStyle}
                  />
                </View>
                <View className="flex-1">
                  <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                    Email
                  </Text>
                  <TextInput
                    value={email}
                    onChangeText={setEmail}
                    placeholder="Optional"
                    placeholderTextColor="#97A3AD"
                    autoCapitalize="none"
                    keyboardType="email-address"
                    className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                    style={inputStyle}
                  />
                </View>
              </View>

              {checkingMatch && (
                <Text className="mt-2 text-[11.5px]" style={{ color: AURORA.ink3 }}>
                  Checking if they&apos;re already tagged…
                </Text>
              )}
              {match && !checkingMatch && (
                <View className="mt-2 flex-row items-center rounded-[11px] px-3 py-2.5" style={{ backgroundColor: AURORA.avBg }}>
                  <Feather name="info" size={14} color={AURORA.avFg} />
                  <Text className="ml-2 flex-1 text-[12px] font-medium" style={{ color: AURORA.avFg }}>
                    Already tagged by someone else — matches {match.name}
                    {match.country ? `, ${match.country}` : ''}. Your tag will link to the same person.
                  </Text>
                </View>
              )}

              <Text className="mb-1.5 mt-3 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                Country
              </Text>
              <TextInput
                value={country}
                onChangeText={setCountry}
                placeholder="Optional"
                placeholderTextColor="#97A3AD"
                className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                style={inputStyle}
              />
            </>
          )}

          <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Nickname <Text style={{ color: AURORA.ink3, fontWeight: '400' }}>(optional)</Text>
          </Text>
          <TextInput
            value={nickname}
            onChangeText={setNickname}
            placeholder="How you know them"
            placeholderTextColor="#97A3AD"
            className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
            style={inputStyle}
          />

          <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Description <Text style={{ color: AURORA.ink3, fontWeight: '400' }}>(optional)</Text>
          </Text>
          <TextInput
            value={description}
            onChangeText={setDescription}
            placeholder="What they're good at, in their own context"
            placeholderTextColor="#97A3AD"
            multiline
            numberOfLines={3}
            className="rounded-[13px] px-3.5 py-3 text-[14px] font-medium"
            style={[inputStyle, { minHeight: 80, textAlignVertical: 'top' }]}
          />

          <View className="mt-4">
            <ChipInput label="Skills" placeholder="e.g. Carpentry" values={skills} onChange={setSkills} />
          </View>

          <View className="mt-4">
            <ChipInput label="Tools" placeholder="e.g. Power saw" values={tools} onChange={setTools} />
            <Pressable
              onPress={handlePickResume}
              disabled={parsingResume}
              className="mt-2 flex-row items-center justify-center rounded-[12px] py-3"
              style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line, opacity: parsingResume ? 0.6 : 1 }}
            >
              {parsingResume ? (
                <ActivityIndicator color={AURORA.primary} size="small" />
              ) : (
                <>
                  <Feather name="upload" size={14} color={AURORA.primary} />
                  <Text className="ml-2 text-[12.5px] font-bold" style={{ color: AURORA.primary }}>
                    Fill tools from a resume
                  </Text>
                </>
              )}
            </Pressable>
          </View>

          <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Years of experience <Text style={{ color: AURORA.ink3, fontWeight: '400' }}>(optional)</Text>
          </Text>
          <TextInput
            value={yearsExperience}
            onChangeText={(t) => setYearsExperience(t.replace(/\D/g, ''))}
            placeholder="e.g. 5"
            placeholderTextColor="#97A3AD"
            keyboardType="number-pad"
            className="h-12 w-24 rounded-[13px] px-3.5 text-[14px] font-medium"
            style={inputStyle}
          />

          <View className="mt-4">
            <ChipInput label="Certifications" placeholder="e.g. AWS Certified" values={certifications} onChange={setCertifications} />
          </View>

          <View className="mt-5 flex-row items-center justify-between rounded-[13px] px-3.5 py-3" style={inputStyle}>
            <View>
              <Text className="text-[13.5px] font-bold" style={{ color: AURORA.ink }}>
                Open to work
              </Text>
              <Text className="mt-0.5 text-[11.5px]" style={{ color: AURORA.ink2 }}>
                Turn off if they&apos;re not available right now.
              </Text>
            </View>
            <Switch value={isOpen} onValueChange={setIsOpen} trackColor={{ true: AURORA.primary }} />
          </View>

          {error && (
            <Text className="mt-3 text-[11px]" style={{ color: AURORA.danger }}>
              {error}
            </Text>
          )}

          <View className="mt-6">
            <PrimaryButton onPress={handleSubmit} loading={submitting} icon="check">
              {isEdit ? 'Save changes' : 'Save tag'}
            </PrimaryButton>
          </View>

          {isEdit && (
            <Pressable onPress={handleDelete} disabled={submitting} className="mt-4 min-h-[44px] items-center justify-center">
              <Text className="text-[13px] font-bold" style={{ color: AURORA.danger }}>
                Remove this tag
              </Text>
            </Pressable>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
