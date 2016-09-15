CC = gcc
CFLAGS =
LDFLAGS =
TARGET = restart_docker_container

SRCS = restart_docker_container.c
OBJS = $(SRCS:.c=.o)

.PHONY: all
all: ${TARGET}

$(TARGET): $(OBJS)
	$(CC) ${LDFLAGS} -o $@ $^

clean:
	rm ${TARGET} ${OBJS}
