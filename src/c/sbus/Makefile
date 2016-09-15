CC = gcc
CFLAGS = -fPIC -Wall -O2
LDFLAGS = -shared
TARGET = libsbus.so
DESTDIR = /usr/local/lib/storlets

SRCS = sbus.c
OBJS = $(SRCS:.c=.o)

.PHONY: all
all: ${TARGET}

$(TARGET): $(OBJS)
	$(CC) ${LDFLAGS} -o $@ $^

install: $(TARGET)
	mkdir -p ${DESTDIR}
	cp ${TARGET} ${DESTDIR}

uninstall:
	rm -rf ${DESTDIR}

clean:
	rm -f ${TARGET} ${OBJS}
