import { refreshSession } from './cognito';
import { clearSession, loadSession, updateAccessToken } from './session';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

/** Loads the stored session, refreshing the access token first if it has expired. */
export async function getValidSession() {
  const session = await loadSession();
  if (!session) return null;

  if (Date.now() < session.expiresAt - 30_000) {
    return session;
  }

  try {
    const refreshed = await refreshSession(session.refreshToken);
    await updateAccessToken(refreshed.accessToken, refreshed.idToken, refreshed.expiresIn);
    return { ...session, accessToken: refreshed.accessToken, idToken: refreshed.idToken };
  } catch {
    await clearSession();
    return null;
  }
}

/** Confirms the backend still accepts the current session (rejects expired/invalid tokens). */
export async function fetchMe(accessToken: string): Promise<{ sub: string } | null> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) return null;
  return response.json();
}

export type Purpose = 'HIRE_OR_STAFF' | 'FIND_WORK' | 'FIND_A_SERVICE' | 'PERSONAL_HOBBY' | 'OTHER';

export const PURPOSE_LABELS: Record<Purpose, string> = {
  HIRE_OR_STAFF: 'Hiring or staffing',
  FIND_WORK: 'Find work',
  FIND_A_SERVICE: 'Find a service',
  PERSONAL_HOBBY: 'Personal / hobby',
  OTHER: 'Other',
};

export type Profile = {
  id: string;
  username: string;
  nickname: string;
  email: string | null;
  purpose: Purpose;
};

/** Returns the signed-in user's profile, or null if onboarding hasn't been completed yet. */
export async function fetchMyProfile(accessToken: string): Promise<Profile | null> {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!response.ok) return null;
  return response.json();
}

export class ProfileError extends Error {}

/** Submits onboarding's identity + purpose step. */
export async function createProfile(
  accessToken: string,
  input: { username: string; nickname: string; email?: string; purpose: Purpose },
): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(input),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ProfileError(typeof data?.message === 'string' ? data.message : 'Could not save your profile.');
  }
  return data;
}

export class ApiError extends Error {}

async function authedJson<T>(accessToken: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}`, ...init?.headers },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(typeof data?.message === 'string' ? data.message : 'Something went wrong.');
  }
  return data as T;
}

// --- Skills (ticket #5) ---

export type Skill = { id: string; name: string; createdAt: string };

export const fetchMySkills = (accessToken: string) => authedJson<Skill[]>(accessToken, '/skills/me');

export const addSkills = (accessToken: string, skills: string[]) =>
  authedJson<Skill[]>(accessToken, '/skills', { method: 'POST', body: JSON.stringify({ skills }) });

export const removeSkill = (accessToken: string, id: string) =>
  authedJson<Skill[]>(accessToken, `/skills/${id}`, { method: 'DELETE' });

/** Uploads a resume file (uri/name/mimeType, as returned by expo-document-picker) and
 * returns dictionary-matched suggestions — nothing is saved by this call. */
export async function suggestSkillsFromResume(
  accessToken: string,
  file: { uri: string; name: string; mimeType: string },
): Promise<string[]> {
  const form = new FormData();
  // React Native's fetch FormData accepts this shape directly; it is not a real Blob.
  form.append('resume', { uri: file.uri, name: file.name, type: file.mimeType } as unknown as Blob);

  const response = await fetch(`${API_BASE_URL}/skills/resume`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(typeof data?.message === 'string' ? data.message : 'Could not read that resume.');
  }
  return data.suggestions as string[];
}

// --- Contact tagging (ticket #6) ---

export type TaggedPersonPreview = { id: string; name: string; country: string | null };

export type Tag = {
  id: string;
  nickname: string | null;
  description: string | null;
  skills: string[];
  tools: string[];
  yearsExperience: number | null;
  certifications: string[];
  isOpen: boolean;
  person: { id: string; name: string; phone: string | null; email: string | null; country: string | null };
};

export type TagInput = {
  personId?: string;
  name: string;
  phone?: string;
  email?: string;
  country?: string;
  nickname?: string;
  description?: string;
  skills: string[];
  tools: string[];
  yearsExperience?: number;
  certifications: string[];
  isOpen: boolean;
};

export const lookupTaggedPerson = (accessToken: string, input: { phone?: string; email?: string }) =>
  authedJson<TaggedPersonPreview | null>(accessToken, '/tagged-people/lookup', {
    method: 'POST',
    body: JSON.stringify(input),
  });

export const fetchMyTags = (accessToken: string) => authedJson<Tag[]>(accessToken, '/tags/mine');

export const createTag = (accessToken: string, input: TagInput) =>
  authedJson<Tag>(accessToken, '/tags', { method: 'POST', body: JSON.stringify(input) });

export const updateTag = (accessToken: string, id: string, input: Partial<TagInput>) =>
  authedJson<Tag>(accessToken, `/tags/${id}`, { method: 'PATCH', body: JSON.stringify(input) });

export const deleteTag = (accessToken: string, id: string) =>
  authedJson<{ success: true }>(accessToken, `/tags/${id}`, { method: 'DELETE' });

// --- Requirements (ticket #8) ---

export type WorkType = 'REMOTE' | 'ON_SITE';

export type Requirement = {
  id: string;
  title: string;
  description: string;
  skillsNeeded: string[];
  workType: WorkType;
  experienceRequired: string | null;
  salary: string | null;
  location: string | null;
  isOpen: boolean;
};

export type RequirementInput = {
  title: string;
  description: string;
  skillsNeeded: string[];
  workType: WorkType;
  experienceRequired?: string;
  salary?: string;
  location?: string;
};

export const fetchMyRequirements = (accessToken: string) =>
  authedJson<Requirement[]>(accessToken, '/requirements/mine');

export const createRequirement = (accessToken: string, input: RequirementInput) =>
  authedJson<Requirement>(accessToken, '/requirements', { method: 'POST', body: JSON.stringify(input) });

export const updateRequirement = (accessToken: string, id: string, input: Partial<RequirementInput & { isOpen: boolean }>) =>
  authedJson<Requirement>(accessToken, `/requirements/${id}`, { method: 'PATCH', body: JSON.stringify(input) });

export const deleteRequirement = (accessToken: string, id: string) =>
  authedJson<{ success: true }>(accessToken, `/requirements/${id}`, { method: 'DELETE' });
