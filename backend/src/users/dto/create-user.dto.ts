import { z } from 'zod';

export const createUserSchema = z.object({
  username: z
    .string()
    .trim()
    .min(3)
    .max(24)
    .regex(/^[a-z0-9_]+$/, 'Username can only contain lowercase letters, numbers, and underscores'),
  nickname: z.string().trim().min(1).max(40),
  email: z.string().trim().toLowerCase().email().optional(),
  purpose: z.enum(['HIRE_OR_STAFF', 'FIND_WORK', 'FIND_A_SERVICE', 'PERSONAL_HOBBY', 'OTHER']),
});

export type CreateUserDto = z.infer<typeof createUserSchema>;
