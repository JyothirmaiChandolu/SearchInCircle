import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { PrimaryButton } from '../src/components/PrimaryButton';
import { AURORA } from '../src/lib/theme';
import { ApiError, addSkills, fetchMySkills, getValidSession, removeSkill, suggestSkillsFromResume, type Skill } from '../src/lib/api';

export default function Skills() {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [newSkill, setNewSkill] = useState('');
  const [adding, setAdding] = useState(false);
  const [parsingResume, setParsingResume] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const session = await getValidSession();
      if (!session) {
        router.replace('/');
        return;
      }
      setAccessToken(session.accessToken);
      try {
        setSkills(await fetchMySkills(session.accessToken));
      } catch {
        setError('Could not load your skills.');
      }
      setLoading(false);
    })();
  }, []);

  const handleAddTyped = async () => {
    if (!accessToken || !newSkill.trim()) return;
    setAdding(true);
    setError(null);
    try {
      setSkills(await addSkills(accessToken, [newSkill.trim()]));
      setNewSkill('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add that skill.');
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (id: string) => {
    if (!accessToken) return;
    setSkills(await removeSkill(accessToken, id));
  };

  const handlePickResume = async () => {
    if (!accessToken) return;
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
      const alreadyHave = new Set(skills.map((s) => s.name.toLowerCase()));
      setSuggestions(found.filter((s) => !alreadyHave.has(s.toLowerCase())));
      setSelectedSuggestions(new Set(found));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not read that resume.');
    } finally {
      setParsingResume(false);
    }
  };

  const toggleSuggestion = (name: string) => {
    setSelectedSuggestions((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleSaveSuggestions = async () => {
    if (!accessToken || selectedSuggestions.size === 0) return;
    setAdding(true);
    setError(null);
    try {
      setSkills(await addSkills(accessToken, [...selectedSuggestions]));
      setSuggestions([]);
      setSelectedSuggestions(new Set());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save those skills.');
    } finally {
      setAdding(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: AURORA.bg }}>
        <ActivityIndicator color={AURORA.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: AURORA.bg }}>
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
            Your skills
          </Text>
        </View>

        <Text className="mb-3 mt-6 text-[13px] font-bold uppercase tracking-wide" style={{ color: AURORA.ink3 }}>
          Current skills
        </Text>
        {skills.length === 0 ? (
          <Text className="text-[13px]" style={{ color: AURORA.ink2 }}>
            Nothing added yet — type one below, or upload a resume.
          </Text>
        ) : (
          <View className="flex-row flex-wrap" style={{ gap: 8 }}>
            {skills.map((skill) => (
              <View
                key={skill.id}
                className="flex-row items-center rounded-full py-2 pl-3.5 pr-2.5"
                style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}
              >
                <Text className="text-[13px] font-semibold" style={{ color: AURORA.ink }}>
                  {skill.name}
                </Text>
                <Pressable onPress={() => handleRemove(skill.id)} className="ml-1.5 h-5 w-5 items-center justify-center">
                  <Feather name="x" size={14} color={AURORA.ink3} />
                </Pressable>
              </View>
            ))}
          </View>
        )}

        <View className="mt-5 flex-row items-center rounded-[15px] p-1" style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}>
          <TextInput
            value={newSkill}
            onChangeText={setNewSkill}
            placeholder="Add a skill, e.g. Plumbing"
            placeholderTextColor="#97A3AD"
            className="h-12 flex-1 px-3 text-[14px] font-medium"
            style={{ color: AURORA.ink }}
            onSubmitEditing={handleAddTyped}
          />
          <Pressable
            onPress={handleAddTyped}
            disabled={adding || !newSkill.trim()}
            className="h-10 items-center justify-center rounded-[11px] px-4"
            style={{ backgroundColor: AURORA.primary, opacity: adding || !newSkill.trim() ? 0.5 : 1 }}
          >
            <Text className="text-[13px] font-bold text-white">Add</Text>
          </Pressable>
        </View>

        <Text className="mb-3 mt-8 text-[13px] font-bold uppercase tracking-wide" style={{ color: AURORA.ink3 }}>
          From a resume
        </Text>
        <Pressable
          onPress={handlePickResume}
          disabled={parsingResume}
          className="flex-row items-center justify-center rounded-[15px] py-4"
          style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line, opacity: parsingResume ? 0.6 : 1 }}
        >
          {parsingResume ? (
            <ActivityIndicator color={AURORA.primary} />
          ) : (
            <>
              <Feather name="upload" size={16} color={AURORA.primary} />
              <Text className="ml-2 text-[14px] font-bold" style={{ color: AURORA.primary }}>
                Upload resume (PDF or text)
              </Text>
            </>
          )}
        </Pressable>

        {suggestions.length > 0 && (
          <View className="mt-4 rounded-[15px] p-4" style={{ backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line }}>
            <Text className="mb-3 text-[12.5px]" style={{ color: AURORA.ink2 }}>
              Found these in your resume — uncheck anything that&apos;s not right, then save.
            </Text>
            <View className="flex-row flex-wrap" style={{ gap: 8 }}>
              {suggestions.map((name) => {
                const selected = selectedSuggestions.has(name);
                return (
                  <Pressable
                    key={name}
                    onPress={() => toggleSuggestion(name)}
                    className="flex-row items-center rounded-full px-3.5 py-2"
                    style={{
                      backgroundColor: selected ? AURORA.avBg : AURORA.surface2,
                      borderWidth: 1,
                      borderColor: selected ? AURORA.primary : AURORA.line,
                    }}
                  >
                    <Feather name={selected ? 'check-square' : 'square'} size={13} color={selected ? AURORA.primary : AURORA.ink3} />
                    <Text
                      className="ml-1.5 text-[12.5px] font-semibold"
                      style={{ color: selected ? AURORA.avFg : AURORA.ink2 }}
                    >
                      {name}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
            <View className="mt-4">
              <PrimaryButton onPress={handleSaveSuggestions} loading={adding} icon="check">
                Save selected
              </PrimaryButton>
            </View>
          </View>
        )}

        {error && (
          <Text className="mt-4 text-[11px]" style={{ color: AURORA.danger }}>
            {error}
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
