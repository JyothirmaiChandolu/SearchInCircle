import { ConflictException, Injectable } from '@nestjs/common';
import { Prisma } from '../generated/prisma/client.js';
import { PrismaService } from '../prisma/prisma.service.js';
import type { CreateUserDto } from './dto/create-user.dto.js';

@Injectable()
export class UsersService {
  constructor(private readonly prisma: PrismaService) {}

  findByCognitoSub(cognitoSub: string) {
    return this.prisma.user.findUnique({ where: { cognitoSub } });
  }

  async create(cognitoSub: string, dto: CreateUserDto) {
    const existing = await this.findByCognitoSub(cognitoSub);
    if (existing) {
      throw new ConflictException('Profile already exists for this account');
    }

    try {
      return await this.prisma.user.create({
        data: { cognitoSub, ...dto },
      });
    } catch (err) {
      if (err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002') {
        const field = (err.meta?.target as string[] | undefined)?.[0];
        if (field === 'username') throw new ConflictException('Username is already taken');
        if (field === 'nickname') throw new ConflictException('Nickname is already taken');
        if (field === 'email') throw new ConflictException('Email is already in use');
      }
      throw err;
    }
  }
}
